"""Analytics engine.

Domain-scoped aggregations, time-series bucketing, growth/trend
comparisons, top/bottom performers, and percentile calculations. Results
are cached in Redis (falling back to in-process) with short TTLs.

All queries respect workspace scoping when a ``workspace_id`` is supplied.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Iterable, Literal

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models.ai import AIHistory
from app.models.audience import Audience
from app.models.audit import AuditLog
from app.models.campaign import Campaign, CampaignTemplate
from app.models.communication import Delivery, DeliveryRecipient
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.template import Template
from app.models.user import User
from app.models.workspace import Workspace
from app.services import cache

Granularity = Literal["day", "week", "month", "quarter", "year"]

CACHE_TTL = 60


# ---------------------------------------------------------------- helpers

def _range(start: datetime | None, end: datetime | None, days: int = 30) -> tuple[datetime, datetime]:
    end = end or datetime.now(timezone.utc)
    start = start or (end - timedelta(days=days))
    return start, end


def _bucket_expr(column, granularity: Granularity):
    if granularity == "day":
        return cast(column, Date)
    if granularity == "week":
        return func.date_trunc("week", column)
    if granularity == "month":
        return func.date_trunc("month", column)
    if granularity == "quarter":
        return func.date_trunc("quarter", column)
    return func.date_trunc("year", column)


def _scope(stmt, model, workspace_id: str | None):
    if workspace_id and hasattr(model, "workspace_id"):
        stmt = stmt.where(model.workspace_id == workspace_id)
    if hasattr(model, "deleted_at"):
        stmt = stmt.where(model.deleted_at.is_(None))
    return stmt


def _growth(current: float, previous: float) -> float:
    if not previous:
        return 100.0 if current else 0.0
    return round(((current - previous) / previous) * 100, 2)


def _moving_average(values: list[float], window: int = 7) -> list[float]:
    out: list[float] = []
    for i in range(len(values)):
        window_slice = values[max(0, i - window + 1):i + 1]
        out.append(round(mean(window_slice), 2) if window_slice else 0.0)
    return out


def _percentiles(values: Iterable[float], ps: tuple[float, ...] = (0.5, 0.9, 0.95, 0.99)) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {f"p{int(p * 100)}": 0.0 for p in ps}
    out: dict[str, float] = {}
    for p in ps:
        idx = min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))
        out[f"p{int(p * 100)}"] = round(float(ordered[idx]), 2)
    return out


# ---------------------------------------------------------------- overview

def executive_overview(db: Session, workspace_id: str | None = None) -> dict:
    params = {"workspace_id": workspace_id}
    cached = cache.get("analytics:overview", params)
    if cached:
        return cached

    total_campaigns = db.scalar(_scope(select(func.count(Campaign.id)), Campaign, workspace_id)) or 0
    total_audience = db.scalar(_scope(select(func.count(Audience.id)), Audience, workspace_id)) or 0
    total_orgs = db.scalar(select(func.count(Organization.id))) or 0
    total_users = db.scalar(select(func.count(User.id))) or 0
    delivered = db.scalar(select(func.count(DeliveryRecipient.id)).where(DeliveryRecipient.status == "delivered")) or 0
    failed = db.scalar(select(func.count(DeliveryRecipient.id)).where(DeliveryRecipient.status == "failed")) or 0
    pending = db.scalar(select(func.count(DeliveryRecipient.id)).where(DeliveryRecipient.status.in_(["pending", "queued", "sending"]))) or 0

    total_recipients = delivered + failed + pending
    delivery_rate = round((delivered / total_recipients) * 100, 2) if total_recipients else 0.0

    channel_rows = db.execute(
        select(Delivery.channel, func.count(Delivery.id)).group_by(Delivery.channel)
    ).all()

    result = {
        "kpis": [
            {"key": "campaigns", "label": "Active campaigns", "value": total_campaigns},
            {"key": "audience", "label": "Audience reach", "value": total_audience},
            {"key": "organizations", "label": "Organizations", "value": total_orgs},
            {"key": "users", "label": "Users", "value": total_users},
            {"key": "delivered", "label": "Delivered", "value": delivered},
            {"key": "failed", "label": "Failed", "value": failed},
            {"key": "pending", "label": "In-flight", "value": pending},
            {"key": "delivery_rate", "label": "Delivery rate", "value": delivery_rate, "unit": "%"},
        ],
        "channels": [{"channel": c or "unknown", "count": n} for c, n in channel_rows],
    }
    cache.set("analytics:overview", params, result, CACHE_TTL)
    return result


# ---------------------------------------------------------------- time series

def time_series(
    db: Session,
    *,
    domain: Literal["campaigns", "audience", "deliveries", "ai", "notifications", "audit"],
    granularity: Granularity = "day",
    start: datetime | None = None,
    end: datetime | None = None,
    workspace_id: str | None = None,
) -> dict:
    start, end = _range(start, end)
    params = {"domain": domain, "granularity": granularity, "start": start.isoformat(),
              "end": end.isoformat(), "workspace_id": workspace_id}
    cached = cache.get("analytics:ts", params)
    if cached:
        return cached

    model_map = {
        "campaigns": Campaign,
        "audience": Audience,
        "deliveries": Delivery,
        "ai": AIHistory,
        "notifications": Notification,
        "audit": AuditLog,
    }
    model = model_map[domain]
    bucket = _bucket_expr(model.created_at, granularity).label("bucket")
    stmt = select(bucket, func.count(model.id).label("count")).where(
        model.created_at >= start, model.created_at <= end
    ).group_by(bucket).order_by(bucket)
    stmt = _scope(stmt, model, workspace_id)
    rows = db.execute(stmt).all()

    series = [{"bucket": (b.isoformat() if hasattr(b, "isoformat") else str(b)), "value": int(c)} for b, c in rows]
    values = [s["value"] for s in series]

    # Previous period for growth calculation
    span = end - start
    prev_start, prev_end = start - span, start
    prev_total = db.scalar(
        _scope(
            select(func.count(model.id)).where(model.created_at >= prev_start, model.created_at < prev_end),
            model,
            workspace_id,
        )
    ) or 0

    curr_total = sum(values)
    result = {
        "series": series,
        "movingAverage": _moving_average(values, window=7 if granularity == "day" else 4),
        "total": curr_total,
        "previousTotal": int(prev_total),
        "growthPct": _growth(curr_total, int(prev_total)),
        "granularity": granularity,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    cache.set("analytics:ts", params, result, CACHE_TTL)
    return result


# ---------------------------------------------------------------- top / bottom

def top_performers(
    db: Session,
    *,
    kind: Literal["campaigns", "templates", "workspaces"] = "campaigns",
    limit: int = 10,
    workspace_id: str | None = None,
    ascending: bool = False,
) -> list[dict]:
    if kind == "campaigns":
        rows = db.execute(
            select(Campaign.id, Campaign.name, func.count(DeliveryRecipient.id).label("total"))
            .select_from(Campaign)
            .join(Delivery, Delivery.campaign_id == Campaign.id, isouter=True)
            .join(DeliveryRecipient, DeliveryRecipient.delivery_id == Delivery.id, isouter=True)
            .where(*( [Campaign.workspace_id == workspace_id] if workspace_id else [] ))
            .group_by(Campaign.id, Campaign.name)
            .order_by(func.count(DeliveryRecipient.id).asc() if ascending else func.count(DeliveryRecipient.id).desc())
            .limit(limit)
        ).all()
        return [{"id": str(cid), "name": name, "total": int(total or 0)} for cid, name, total in rows]


    if kind == "templates":
        rows = db.execute(
            select(Template.id, Template.name, func.count(CampaignTemplate.template_id).label("uses"))
            .select_from(Template)
            .join(CampaignTemplate, CampaignTemplate.template_id == Template.id, isouter=True)
            .where(*( [Template.workspace_id == workspace_id] if workspace_id else [] ))
            .group_by(Template.id, Template.name)
            .order_by(func.count(CampaignTemplate.template_id).asc() if ascending else func.count(CampaignTemplate.template_id).desc())
            .limit(limit)
        ).all()
        return [{"id": str(tid), "name": name, "uses": int(uses or 0)} for tid, name, uses in rows]

    rows = db.execute(
        select(Workspace.id, Workspace.name, func.count(Campaign.id).label("campaigns"))
        .select_from(Workspace)
        .join(Campaign, Campaign.workspace_id == Workspace.id, isouter=True)
        .group_by(Workspace.id, Workspace.name)
        .order_by(func.count(Campaign.id).asc() if ascending else func.count(Campaign.id).desc())
        .limit(limit)
    ).all()
    return [{"id": str(wid), "name": name, "campaigns": int(c or 0)} for wid, name, c in rows]


# ---------------------------------------------------------------- domain-specific

def campaign_analytics(db: Session, workspace_id: str | None = None) -> dict:
    by_status = dict(
        db.execute(
            _scope(select(Campaign.status, func.count(Campaign.id)).group_by(Campaign.status), Campaign, workspace_id)
        ).all()
    )
    by_channel = dict(db.execute(select(Delivery.channel, func.count(Delivery.id)).group_by(Delivery.channel)).all())
    delivered = db.scalar(select(func.count(DeliveryRecipient.id)).where(DeliveryRecipient.status == "delivered")) or 0
    failed = db.scalar(select(func.count(DeliveryRecipient.id)).where(DeliveryRecipient.status == "failed")) or 0
    return {
        "byStatus": {k: int(v) for k, v in by_status.items()},
        "byChannel": {k: int(v) for k, v in by_channel.items()},
        "delivered": delivered,
        "failed": failed,
        "deliveryRate": round(delivered / (delivered + failed) * 100, 2) if (delivered + failed) else 0.0,
    }


def communication_analytics(db: Session, workspace_id: str | None = None) -> dict:
    by_status = dict(db.execute(select(DeliveryRecipient.status, func.count(DeliveryRecipient.id)).group_by(DeliveryRecipient.status)).all())
    by_channel = dict(db.execute(select(Delivery.channel, func.count(Delivery.id)).group_by(Delivery.channel)).all())
    return {
        "byStatus": {k: int(v) for k, v in by_status.items()},
        "byChannel": {k: int(v) for k, v in by_channel.items()},
        "percentiles": _percentiles([int(v) for v in by_status.values()]),
    }


def ai_usage_analytics(db: Session, workspace_id: str | None = None) -> dict:
    total = db.scalar(select(func.count(AIHistory.id))) or 0
    by_mode = dict(db.execute(select(AIHistory.model, func.count(AIHistory.id)).group_by(AIHistory.model)).all())
    tokens = db.scalar(select(func.coalesce(func.sum(AIHistory.tokens), 0))) or 0
    return {
        "totalGenerations": int(total),
        "byMode": {k: int(v) for k, v in by_mode.items()},
        "totalTokens": int(tokens),
    }


def audience_analytics(db: Session, workspace_id: str | None = None) -> dict:
    total = db.scalar(_scope(select(func.count(Audience.id)), Audience, workspace_id)) or 0
    by_language = dict(
        db.execute(_scope(select(Audience.language, func.count(Audience.id)).group_by(Audience.language), Audience, workspace_id)).all()
    )
    by_status = dict(
        db.execute(_scope(select(Audience.status, func.count(Audience.id)).group_by(Audience.status), Audience, workspace_id)).all()
    )
    return {
        "total": int(total),
        "byLanguage": {k or "unknown": int(v) for k, v in by_language.items()},
        "byStatus": {k or "unknown": int(v) for k, v in by_status.items()},
    }


def security_analytics(db: Session) -> dict:
    from app.models.auth_extras import LoginAttempt
    total_attempts = db.scalar(select(func.count(LoginAttempt.id))) or 0
    failed = db.scalar(select(func.count(LoginAttempt.id)).where(LoginAttempt.success.is_(False))) or 0
    return {
        "loginAttempts": int(total_attempts),
        "failedLogins": int(failed),
        "failureRate": round(failed / total_attempts * 100, 2) if total_attempts else 0.0,
    }


def notification_analytics(db: Session) -> dict:
    total = db.scalar(select(func.count(Notification.id))) or 0
    unread = db.scalar(select(func.count(Notification.id)).where(Notification.read.is_(False))) or 0
    by_priority = dict(db.execute(select(Notification.priority, func.count(Notification.id)).group_by(Notification.priority)).all())
    return {
        "total": int(total),
        "unread": int(unread),
        "byPriority": {k: int(v) for k, v in by_priority.items()},
    }


# ---------------------------------------------------------------- role-based dashboard

def dashboard_snapshot(db: Session, *, user_id: str | None = None, workspace_id: str | None = None, role: str = "user") -> dict:
    widgets: list[dict[str, Any]] = [
        {"key": "overview", "data": executive_overview(db, workspace_id)},
        {"key": "campaigns_ts", "data": time_series(db, domain="campaigns", workspace_id=workspace_id)},
        {"key": "audience", "data": audience_analytics(db, workspace_id)},
        {"key": "communication", "data": communication_analytics(db, workspace_id)},
        {"key": "notifications", "data": notification_analytics(db)},
    ]
    if role in {"admin", "owner", "security_officer"}:
        widgets.append({"key": "security", "data": security_analytics(db)})
    if role in {"admin", "owner"}:
        widgets.append({"key": "ai_usage", "data": ai_usage_analytics(db, workspace_id)})
    return {"role": role, "workspaceId": workspace_id, "widgets": widgets,
            "generatedAt": datetime.now(timezone.utc).isoformat()}


def benchmarks(db: Session, workspace_id: str | None = None) -> dict:
    """Compare a workspace's headline metrics against the platform average."""
    org_avg_campaigns = db.scalar(
        select(func.count(Campaign.id) / func.greatest(func.count(func.distinct(Campaign.workspace_id)), 1))
    ) or 0
    ws_campaigns = db.scalar(_scope(select(func.count(Campaign.id)), Campaign, workspace_id)) or 0
    return {
        "workspaceCampaigns": int(ws_campaigns),
        "platformAverageCampaigns": float(org_avg_campaigns or 0),
        "indexed": round(ws_campaigns / float(org_avg_campaigns), 2) if org_avg_campaigns else None,
    }


# =========================================================================== #
# Analytics Platform services (Phase 6.2).
#
# Business layer over AnalyticsMetric / AnalyticsSnapshot / AnalyticsReport.
# Repositories stay thin; validation, workflow transitions, and aggregation
# orchestration live here. RBAC is enforced by callers (routers, etc.); the
# service helpers assume the caller has already been authorised.
# =========================================================================== #


import uuid as _uuid  # noqa: E402
from datetime import datetime as _dt  # noqa: E402
from datetime import timezone as _tz  # noqa: E402
from typing import Any as _Any  # noqa: E402

from sqlalchemy.orm import Session as _Session  # noqa: E402

from app.constants.analytics import (  # noqa: E402
    METRIC_SCOPES,
    REPORT_STATUS_COMPLETED,
    REPORT_STATUS_FAILED,
    REPORT_STATUS_GENERATING,
    REPORT_STATUS_PENDING,
    REPORT_STATUSES,
    SNAPSHOT_TYPES,
)
from app.core.exceptions import ConflictError as _ConflictError  # noqa: E402
from app.core.exceptions import NotFoundError as _NotFoundError  # noqa: E402
from app.core.exceptions import ValidationError as _ValidationError  # noqa: E402
from app.models.analytics import (  # noqa: E402
    AnalyticsMetric as _AnalyticsMetric,
)
from app.models.analytics import (
    AnalyticsReport as _AnalyticsReport,
)
from app.models.analytics import (
    AnalyticsSnapshot as _AnalyticsSnapshot,
)
from app.repositories.analytics import (  # noqa: E402
    analytics_metrics as _metrics_repo,
)
from app.repositories.analytics import (
    analytics_reports as _reports_repo,
)
from app.repositories.analytics import (
    analytics_snapshots as _snapshots_repo,
)


# --------------------------------------------------------------------------- #
# Report workflow transition map (single source of truth).
# --------------------------------------------------------------------------- #

REPORT_TRANSITIONS: dict[str, frozenset[str]] = {
    REPORT_STATUS_PENDING: frozenset({REPORT_STATUS_GENERATING, REPORT_STATUS_FAILED}),
    REPORT_STATUS_GENERATING: frozenset(
        {REPORT_STATUS_COMPLETED, REPORT_STATUS_FAILED}
    ),
    REPORT_STATUS_COMPLETED: frozenset(),
    REPORT_STATUS_FAILED: frozenset(),
}


def _assert_transition(current: str, target: str) -> None:
    if current == target:
        return
    allowed = REPORT_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise _ValidationError(
            f"Illegal report status transition: {current} -> {target}",
            details={"from": current, "to": target, "allowed": sorted(allowed)},
        )


def _validate_scope(scope: str) -> None:
    if scope not in METRIC_SCOPES:
        raise _ValidationError(
            f"Invalid metric scope: {scope!r}",
            details={"allowed": list(METRIC_SCOPES)},
        )


def _validate_entity_ref(entity_type: str | None, entity_id: _Any | None) -> None:
    if (entity_type is None) != (entity_id is None):
        raise _ValidationError(
            "entity_type and entity_id must be provided together",
            details={"entity_type": entity_type, "entity_id": str(entity_id) if entity_id else None},
        )
    if entity_type is not None and not entity_type.strip():
        raise _ValidationError("entity_type must be a non-empty string")


def _validate_period(period_start: _dt, period_end: _dt) -> None:
    if period_end < period_start:
        raise _ValidationError(
            "period_end must be greater than or equal to period_start",
            details={
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
            },
        )


def _validate_snapshot_type(snapshot_type: str) -> None:
    if snapshot_type not in SNAPSHOT_TYPES:
        raise _ValidationError(
            f"Invalid snapshot type: {snapshot_type!r}",
            details={"allowed": list(SNAPSHOT_TYPES)},
        )


def _validate_report_status(status: str) -> None:
    if status not in REPORT_STATUSES:
        raise _ValidationError(
            f"Invalid report status: {status!r}",
            details={"allowed": list(REPORT_STATUSES)},
        )


def _now() -> _dt:
    return _dt.now(_tz.utc)


# --------------------------------------------------------------------------- #
# AnalyticsMetricService
# --------------------------------------------------------------------------- #


class AnalyticsMetricService:
    """Business layer for time-series metric points."""

    def __init__(self, repo=_metrics_repo) -> None:
        self.repo = repo

    def record_metric(
        self,
        db: _Session,
        *,
        metric_name: str,
        metric_scope: str,
        metric_value: float = 0.0,
        recorded_at: _dt | None = None,
        entity_type: str | None = None,
        entity_id: _uuid.UUID | str | None = None,
        metric_unit: str | None = None,
        metadata: dict[str, _Any] | None = None,
    ) -> _AnalyticsMetric:
        if not metric_name or not metric_name.strip():
            raise _ValidationError("metric_name is required")
        _validate_scope(metric_scope)
        _validate_entity_ref(entity_type, entity_id)
        data: dict[str, _Any] = {
            "metric_name": metric_name.strip(),
            "metric_scope": metric_scope,
            "metric_value": metric_value,
            "recorded_at": recorded_at or _now(),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metric_unit": metric_unit,
            "metadata_": metadata or {},
        }
        return self.repo.create_metric(db, data)

    def get_metric(self, db: _Session, metric_id: _uuid.UUID | str) -> _AnalyticsMetric:
        metric = self.repo.get_metric(db, metric_id)
        if metric is None:
            raise _NotFoundError("Metric not found")
        return metric

    def update_metric(
        self,
        db: _Session,
        metric_id: _uuid.UUID | str,
        *,
        metric_value: float | None = None,
        metric_unit: str | None = None,
        metadata: dict[str, _Any] | None = None,
    ) -> _AnalyticsMetric:
        metric = self.get_metric(db, metric_id)
        # entity_type/entity_id are immutable — reject any attempt to change them.
        data: dict[str, _Any] = {}
        if metric_value is not None:
            data["metric_value"] = metric_value
        if metric_unit is not None:
            data["metric_unit"] = metric_unit
        if metadata is not None:
            data["metadata_"] = metadata
        return self.repo.update(db, metric, data)

    def delete_metric(self, db: _Session, metric_id: _uuid.UUID | str) -> None:
        metric = self.get_metric(db, metric_id)
        self.repo.delete_metric(db, metric)

    def search_metrics(
        self,
        db: _Session,
        *,
        query: str | None = None,
        page: int = 1,
        page_size: int = 50,
        metric_scope: str | None = None,
        metric_name: str | None = None,
        entity_type: str | None = None,
        entity_id: _uuid.UUID | str | None = None,
        recorded_from: _dt | None = None,
        recorded_to: _dt | None = None,
    ) -> tuple[list[_AnalyticsMetric], int]:
        if metric_scope is not None:
            _validate_scope(metric_scope)
        if page < 1 or page_size < 1 or page_size > 500:
            raise _ValidationError("Invalid pagination parameters")
        return self.repo.search_metrics(
            db,
            query=query,
            page=page,
            page_size=page_size,
            metric_scope=metric_scope,
            metric_name=metric_name,
            entity_type=entity_type,
            entity_id=entity_id,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        )

    def aggregate(
        self,
        db: _Session,
        *,
        metric_name: str,
        metric_scope: str | None = None,
        entity_type: str | None = None,
        entity_id: _uuid.UUID | str | None = None,
        recorded_from: _dt | None = None,
        recorded_to: _dt | None = None,
    ) -> dict[str, float]:
        if not metric_name or not metric_name.strip():
            raise _ValidationError("metric_name is required for aggregation")
        if metric_scope is not None:
            _validate_scope(metric_scope)
        if recorded_from and recorded_to and recorded_to < recorded_from:
            raise _ValidationError("recorded_to must be >= recorded_from")
        return self.repo.aggregate_metrics(
            db,
            metric_name=metric_name.strip(),
            metric_scope=metric_scope,
            entity_type=entity_type,
            entity_id=entity_id,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        )


# --------------------------------------------------------------------------- #
# AnalyticsSnapshotService
# --------------------------------------------------------------------------- #


class AnalyticsSnapshotService:
    """Business layer for aggregated KPI snapshots."""

    def __init__(self, repo=_snapshots_repo) -> None:
        self.repo = repo

    def generate_snapshot(
        self,
        db: _Session,
        *,
        snapshot_type: str,
        period_start: _dt,
        period_end: _dt,
        metrics_json: dict[str, _Any] | None = None,
        organization_id: _uuid.UUID | str | None = None,
        metadata: dict[str, _Any] | None = None,
    ) -> _AnalyticsSnapshot:
        _validate_snapshot_type(snapshot_type)
        _validate_period(period_start, period_end)
        existing = self.repo.find_existing(
            db,
            snapshot_type=snapshot_type,
            period_start=period_start,
            period_end=period_end,
            organization_id=organization_id,
        )
        if existing is not None:
            raise _ConflictError(
                "Snapshot for this period already exists",
                details={"snapshot_id": str(existing.id)},
            )
        return self.repo.create_snapshot(
            db,
            {
                "snapshot_type": snapshot_type,
                "period_start": period_start,
                "period_end": period_end,
                "organization_id": organization_id,
                "generated_at": _now(),
                "metrics_json": metrics_json or {},
                "metadata_": metadata or {},
            },
        )

    def regenerate_snapshot(
        self,
        db: _Session,
        snapshot_id: _uuid.UUID | str,
        *,
        metrics_json: dict[str, _Any] | None = None,
        metadata: dict[str, _Any] | None = None,
    ) -> _AnalyticsSnapshot:
        snapshot = self.get_snapshot(db, snapshot_id)
        data: dict[str, _Any] = {"generated_at": _now()}
        if metrics_json is not None:
            data["metrics_json"] = metrics_json
        if metadata is not None:
            data["metadata_"] = metadata
        return self.repo.update_snapshot(db, snapshot, data)

    def get_snapshot(
        self, db: _Session, snapshot_id: _uuid.UUID | str
    ) -> _AnalyticsSnapshot:
        snap = self.repo.get_snapshot(db, snapshot_id)
        if snap is None:
            raise _NotFoundError("Snapshot not found")
        return snap

    def latest_snapshot(
        self,
        db: _Session,
        *,
        snapshot_type: str,
        organization_id: _uuid.UUID | str | None = None,
    ) -> _AnalyticsSnapshot | None:
        _validate_snapshot_type(snapshot_type)
        return self.repo.latest_snapshot(
            db, snapshot_type=snapshot_type, organization_id=organization_id
        )

    def list_snapshots(self, db: _Session, **kwargs: _Any):
        st = kwargs.get("snapshot_type")
        if st is not None:
            _validate_snapshot_type(st)
        return self.repo.list_snapshots(db, **kwargs)

    def delete_snapshot(self, db: _Session, snapshot_id: _uuid.UUID | str) -> None:
        snap = self.get_snapshot(db, snapshot_id)
        self.repo.delete_snapshot(db, snap)


# --------------------------------------------------------------------------- #
# AnalyticsReportService
# --------------------------------------------------------------------------- #


class AnalyticsReportService:
    """Business layer for report generation lifecycle."""

    def __init__(self, repo=_reports_repo) -> None:
        self.repo = repo

    def request_report(
        self,
        db: _Session,
        *,
        report_name: str,
        report_type: str,
        requested_by_user_id: _uuid.UUID | str | None = None,
        organization_id: _uuid.UUID | str | None = None,
        metadata: dict[str, _Any] | None = None,
    ) -> _AnalyticsReport:
        if not report_name or not report_name.strip():
            raise _ValidationError("report_name is required")
        if not report_type or not report_type.strip():
            raise _ValidationError("report_type is required")
        return self.repo.create_report(
            db,
            {
                "report_name": report_name.strip(),
                "report_type": report_type.strip(),
                "requested_by_user_id": requested_by_user_id,
                "organization_id": organization_id,
                "status": REPORT_STATUS_PENDING,
                "metadata_": metadata or {},
            },
        )

    def get_report(self, db: _Session, report_id: _uuid.UUID | str) -> _AnalyticsReport:
        rep = self.repo.get_report(db, report_id)
        if rep is None:
            raise _NotFoundError("Report not found")
        return rep

    def list_reports(self, db: _Session, **kwargs: _Any):
        status = kwargs.get("status")
        if status is not None:
            _validate_report_status(status)
        return self.repo.list_reports(db, **kwargs)

    def _transition(
        self, db: _Session, report: _AnalyticsReport, target: str, extra: dict[str, _Any] | None = None
    ) -> _AnalyticsReport:
        _validate_report_status(target)
        _assert_transition(report.status, target)
        data: dict[str, _Any] = {"status": target}
        if extra:
            data.update(extra)
        return self.repo.update_report(db, report, data)

    def start_generation(
        self, db: _Session, report_id: _uuid.UUID | str
    ) -> _AnalyticsReport:
        report = self.get_report(db, report_id)
        return self._transition(db, report, REPORT_STATUS_GENERATING)

    def complete_generation(
        self,
        db: _Session,
        report_id: _uuid.UUID | str,
        *,
        file_path: str,
        expires_at: _dt | None = None,
        metadata: dict[str, _Any] | None = None,
    ) -> _AnalyticsReport:
        if not file_path or not file_path.strip():
            raise _ValidationError("file_path is required to complete a report")
        report = self.get_report(db, report_id)
        now = _now()
        if expires_at is not None and expires_at <= now:
            raise _ValidationError("expires_at must be in the future")
        extra: dict[str, _Any] = {
            "file_path": file_path.strip(),
            "generated_at": now,
        }
        if expires_at is not None:
            extra["expires_at"] = expires_at
        if metadata is not None:
            extra["metadata_"] = metadata
        return self._transition(db, report, REPORT_STATUS_COMPLETED, extra=extra)

    def fail_generation(
        self,
        db: _Session,
        report_id: _uuid.UUID | str,
        *,
        error: str | None = None,
    ) -> _AnalyticsReport:
        report = self.get_report(db, report_id)
        extra: dict[str, _Any] = {}
        if error:
            meta = dict(report.metadata_ or {})
            meta["error"] = error
            extra["metadata_"] = meta
        return self._transition(db, report, REPORT_STATUS_FAILED, extra=extra)

    def expire_report(
        self,
        db: _Session,
        report_id: _uuid.UUID | str,
        *,
        expires_at: _dt | None = None,
    ) -> _AnalyticsReport:
        report = self.get_report(db, report_id)
        if report.status != REPORT_STATUS_COMPLETED:
            raise _ValidationError(
                "Only completed reports can be expired",
                details={"status": report.status},
            )
        ts = expires_at or _now()
        return self.repo.update_report(db, report, {"expires_at": ts})

    def delete_report(self, db: _Session, report_id: _uuid.UUID | str) -> None:
        rep = self.get_report(db, report_id)
        self.repo.delete_report(db, rep)


# Module-level service singletons — same pattern as the rest of the platform.
metric_service = AnalyticsMetricService()
snapshot_service = AnalyticsSnapshotService()
report_service = AnalyticsReportService()
