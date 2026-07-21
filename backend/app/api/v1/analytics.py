from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import current_user, require_perm
from app.dependencies.db import get_db
from app.models.user import User
from app.services import analytics, analytics_events, audit

router = APIRouter()


@router.get("/overview")
def overview(
    workspace_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    return ok(analytics.executive_overview(db, workspace_id))


@router.get("/time-series")
def time_series(
    domain: str = Query("campaigns"),
    granularity: str = Query("day", pattern="^(day|week|month|quarter|year)$"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    workspace_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    return ok(analytics.time_series(
        db, domain=domain, granularity=granularity,  # type: ignore[arg-type]
        start=start, end=end, workspace_id=workspace_id,
    ))


@router.get("/top")
def top(
    kind: str = Query("campaigns", pattern="^(campaigns|templates|workspaces)$"),
    limit: int = Query(10, ge=1, le=100),
    workspace_id: str | None = Query(None),
    ascending: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    return ok(analytics.top_performers(
        db, kind=kind, limit=limit, workspace_id=workspace_id, ascending=ascending,  # type: ignore[arg-type]
    ))


@router.get("/campaigns")
def campaigns(workspace_id: str | None = Query(None), db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:view"))):
    return ok(analytics.campaign_analytics(db, workspace_id))


@router.get("/audience")
def audience(workspace_id: str | None = Query(None), db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:view"))):
    return ok(analytics.audience_analytics(db, workspace_id))


@router.get("/communication")
def communication(workspace_id: str | None = Query(None), db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:view"))):
    return ok(analytics.communication_analytics(db, workspace_id))


@router.get("/ai")
def ai_usage(workspace_id: str | None = Query(None), db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:view"))):
    return ok(analytics.ai_usage_analytics(db, workspace_id))


@router.get("/security")
def security(db: Session = Depends(get_db), _: User = Depends(require_perm("security:view"))):
    return ok(analytics.security_analytics(db))


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:view"))):
    return ok(analytics.notification_analytics(db))


@router.get("/benchmarks")
def benchmarks(workspace_id: str | None = Query(None), db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:view"))):
    return ok(analytics.benchmarks(db, workspace_id))


@router.get("/dashboard")
def dashboard(
    workspace_id: str | None = Query(None),
    role: str = Query("user"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return ok(analytics.dashboard_snapshot(db, user_id=str(user.id), workspace_id=workspace_id, role=role))


# =========================================================================== #
# Phase 6.3 — Analytics Platform (Metrics / Snapshots / Reports)              #
# --------------------------------------------------------------------------- #
# Thin routes over app.services.analytics platform services.                  #
# All validation, workflow, and RBAC-domain rules live in the service layer.  #
# =========================================================================== #

import uuid as _uuid
from typing import Any as _Any

from fastapi import Body

from app.core.responses import paginated
from app.models.analytics import (
    AnalyticsMetric as _AnalyticsMetric,
    AnalyticsReport as _AnalyticsReport,
    AnalyticsSnapshot as _AnalyticsSnapshot,
)
from app.schemas.analytics import (
    AnalyticsMetricCreate,
    AnalyticsMetricUpdate,
    AnalyticsReportCreate,
    AnalyticsSnapshotCreate,
)
from app.services.analytics import (
    metric_service as _metric_service,
    report_service as _report_service,
    snapshot_service as _snapshot_service,
)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _serialize_metric(m: _AnalyticsMetric) -> dict[str, _Any]:
    return {
        "id": str(m.id),
        "metricName": m.metric_name,
        "metricScope": m.metric_scope,
        "entityType": m.entity_type,
        "entityId": str(m.entity_id) if m.entity_id else None,
        "metricValue": float(m.metric_value) if m.metric_value is not None else 0.0,
        "metricUnit": m.metric_unit,
        "recordedAt": _iso(m.recorded_at),
        "metadata": dict(m.metadata_ or {}),
        "createdAt": _iso(m.created_at),
        "updatedAt": _iso(m.updated_at),
    }


def _serialize_snapshot(s: _AnalyticsSnapshot) -> dict[str, _Any]:
    return {
        "id": str(s.id),
        "snapshotType": s.snapshot_type,
        "organizationId": str(s.organization_id) if s.organization_id else None,
        "periodStart": _iso(s.period_start),
        "periodEnd": _iso(s.period_end),
        "generatedAt": _iso(s.generated_at),
        "metricsJson": dict(s.metrics_json or {}),
        "metadata": dict(s.metadata_ or {}),
        "createdAt": _iso(s.created_at),
        "updatedAt": _iso(s.updated_at),
    }


def _serialize_report(r: _AnalyticsReport) -> dict[str, _Any]:
    return {
        "id": str(r.id),
        "reportName": r.report_name,
        "reportType": r.report_type,
        "requestedByUserId": str(r.requested_by_user_id) if r.requested_by_user_id else None,
        "organizationId": str(r.organization_id) if r.organization_id else None,
        "status": r.status,
        "filePath": r.file_path,
        "generatedAt": _iso(r.generated_at),
        "expiresAt": _iso(r.expires_at),
        "metadata": dict(r.metadata_ or {}),
        "createdAt": _iso(r.created_at),
        "updatedAt": _iso(r.updated_at),
    }


# --------------------------------------------------------------------------- #
# Snapshots  (registered before /{metric_id} to prevent shadowing)
# --------------------------------------------------------------------------- #


@router.get("/snapshots/latest", response_model=None, summary="Latest snapshot")
def latest_snapshot(
    snapshot_type: str = Query(..., alias="snapshotType"),
    organization_id: str | None = Query(None, alias="organizationId"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    snap = _snapshot_service.latest_snapshot(
        db, snapshot_type=snapshot_type, organization_id=organization_id
    )
    return ok(_serialize_snapshot(snap) if snap else None)


@router.get("/snapshots", response_model=None, summary="List snapshots")
def list_snapshots(
    snapshot_type: str | None = Query(None, alias="snapshotType"),
    organization_id: str | None = Query(None, alias="organizationId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500, alias="pageSize"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    items, total = _snapshot_service.list_snapshots(
        db,
        snapshot_type=snapshot_type,
        organization_id=organization_id,
        page=page,
        page_size=page_size,
    )
    return paginated([_serialize_snapshot(s) for s in items], page, page_size, total)


@router.post("/snapshots", status_code=201, response_model=None, summary="Generate a snapshot")
def create_snapshot(
    payload: AnalyticsSnapshotCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    snap = _snapshot_service.generate_snapshot(
        db,
        snapshot_type=payload.snapshotType,
        period_start=payload.periodStart,
        period_end=payload.periodEnd,
        metrics_json=dict(payload.metricsJson or {}),
        organization_id=payload.organizationId,
        metadata=dict(payload.metadata or {}),
    )
    audit.log(db, action="create", module="analytics_snapshot", actor_id=user.id,
              entity_id=str(snap.id), entity_label=snap.snapshot_type)
    analytics_events.snapshot_created(db, snap, actor_id=user.id)
    return ok(_serialize_snapshot(snap))


@router.get("/snapshots/{snapshot_id}", response_model=None, summary="Get snapshot")
def get_snapshot(
    snapshot_id: _uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    return ok(_serialize_snapshot(_snapshot_service.get_snapshot(db, snapshot_id)))


@router.post(
    "/snapshots/{snapshot_id}/regenerate",
    response_model=None,
    summary="Regenerate snapshot",
)
def regenerate_snapshot(
    snapshot_id: _uuid.UUID,
    payload: dict[str, _Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    snap = _snapshot_service.regenerate_snapshot(
        db,
        snapshot_id,
        metrics_json=payload.get("metricsJson"),
        metadata=payload.get("metadata"),
    )
    audit.log(db, action="regenerate", module="analytics_snapshot", actor_id=user.id,
              entity_id=str(snap.id), entity_label=snap.snapshot_type)
    analytics_events.snapshot_regenerated(db, snap, actor_id=user.id)
    return ok(_serialize_snapshot(snap))


@router.delete("/snapshots/{snapshot_id}", response_model=None, summary="Delete snapshot")
def delete_snapshot(
    snapshot_id: _uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    snap = _snapshot_service.get_snapshot(db, snapshot_id)
    analytics_events.snapshot_deleted(db, snap, actor_id=user.id)
    _snapshot_service.delete_snapshot(db, snapshot_id)
    audit.log(db, action="delete", module="analytics_snapshot", actor_id=user.id,
              entity_id=str(snapshot_id))
    return ok({"deleted": True, "id": str(snapshot_id)})


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #


@router.get("/reports", response_model=None, summary="List reports")
def list_reports(
    status: str | None = Query(None),
    report_type: str | None = Query(None, alias="reportType"),
    organization_id: str | None = Query(None, alias="organizationId"),
    requested_by_user_id: str | None = Query(None, alias="requestedByUserId"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500, alias="pageSize"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    items, total = _report_service.list_reports(
        db,
        status=status,
        report_type=report_type,
        organization_id=organization_id,
        requested_by_user_id=requested_by_user_id,
        page=page,
        page_size=page_size,
    )
    return paginated([_serialize_report(r) for r in items], page, page_size, total)


@router.post("/reports", status_code=201, response_model=None, summary="Request a report")
def create_report(
    payload: AnalyticsReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:export")),
):
    report = _report_service.request_report(
        db,
        report_name=payload.reportName,
        report_type=payload.reportType,
        requested_by_user_id=payload.requestedByUserId or user.id,
        organization_id=payload.organizationId,
        metadata=dict(payload.metadata or {}),
    )
    audit.log(db, action="request", module="analytics_report", actor_id=user.id,
              entity_id=str(report.id), entity_label=report.report_name)
    analytics_events.report_requested(db, report, actor_id=user.id)
    return ok(_serialize_report(report))


@router.get("/reports/{report_id}", response_model=None, summary="Get report")
def get_report(
    report_id: _uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    return ok(_serialize_report(_report_service.get_report(db, report_id)))


@router.post("/reports/{report_id}/start", response_model=None, summary="Start report")
def start_report(
    report_id: _uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    report = _report_service.start_generation(db, report_id)
    audit.log(db, action="start_generation", module="analytics_report", actor_id=user.id,
              entity_id=str(report.id), entity_label=report.report_name)
    analytics_events.report_generation_started(db, report, actor_id=user.id)
    return ok(_serialize_report(report))


@router.post("/reports/{report_id}/complete", response_model=None, summary="Complete report")
def complete_report(
    report_id: _uuid.UUID,
    payload: dict[str, _Any] = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    expires_raw = payload.get("expiresAt")
    expires_at = (
        datetime.fromisoformat(expires_raw) if isinstance(expires_raw, str) else expires_raw
    )
    report = _report_service.complete_generation(
        db,
        report_id,
        file_path=payload.get("filePath", ""),
        expires_at=expires_at,
        metadata=payload.get("metadata"),
    )
    audit.log(db, action="complete_generation", module="analytics_report", actor_id=user.id,
              entity_id=str(report.id), entity_label=report.report_name)
    analytics_events.report_generation_completed(db, report, actor_id=user.id)
    return ok(_serialize_report(report))


@router.post("/reports/{report_id}/fail", response_model=None, summary="Fail report")
def fail_report(
    report_id: _uuid.UUID,
    payload: dict[str, _Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    error = payload.get("error")
    report = _report_service.fail_generation(db, report_id, error=error)
    audit.log(db, action="fail_generation", module="analytics_report", actor_id=user.id,
              entity_id=str(report.id), entity_label=report.report_name,
              metadata={"error": error} if error else None)
    analytics_events.report_generation_failed(db, report, actor_id=user.id)
    return ok(_serialize_report(report))


@router.post("/reports/{report_id}/expire", response_model=None, summary="Expire report")
def expire_report(
    report_id: _uuid.UUID,
    payload: dict[str, _Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    expires_raw = payload.get("expiresAt")
    expires_at = (
        datetime.fromisoformat(expires_raw) if isinstance(expires_raw, str) else expires_raw
    )
    report = _report_service.expire_report(db, report_id, expires_at=expires_at)
    audit.log(db, action="expire", module="analytics_report", actor_id=user.id,
              entity_id=str(report.id), entity_label=report.report_name)
    analytics_events.report_expired(db, report, actor_id=user.id)
    return ok(_serialize_report(report))


@router.delete("/reports/{report_id}", response_model=None, summary="Delete report")
def delete_report(
    report_id: _uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    report = _report_service.get_report(db, report_id)
    analytics_events.report_deleted(db, report, actor_id=user.id)
    _report_service.delete_report(db, report_id)
    audit.log(db, action="delete", module="analytics_report", actor_id=user.id,
              entity_id=str(report_id), entity_label=report.report_name)
    return ok({"deleted": True, "id": str(report_id)})


# --------------------------------------------------------------------------- #
# Metrics  (registered LAST — /{metric_id} would otherwise shadow literals)
# --------------------------------------------------------------------------- #


@router.get("/aggregate", response_model=None, summary="Aggregate metric values")
def aggregate_metrics(
    metric_name: str = Query(..., alias="metricName"),
    metric_scope: str | None = Query(None, alias="metricScope"),
    entity_type: str | None = Query(None, alias="entityType"),
    entity_id: str | None = Query(None, alias="entityId"),
    recorded_from: datetime | None = Query(None, alias="recordedFrom"),
    recorded_to: datetime | None = Query(None, alias="recordedTo"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    return ok(
        _metric_service.aggregate(
            db,
            metric_name=metric_name,
            metric_scope=metric_scope,
            entity_type=entity_type,
            entity_id=entity_id,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        )
    )


@router.get("", response_model=None, summary="List metrics")
def list_metrics(
    q: str | None = Query(None),
    metric_scope: str | None = Query(None, alias="metricScope"),
    metric_name: str | None = Query(None, alias="metricName"),
    entity_type: str | None = Query(None, alias="entityType"),
    entity_id: str | None = Query(None, alias="entityId"),
    recorded_from: datetime | None = Query(None, alias="recordedFrom"),
    recorded_to: datetime | None = Query(None, alias="recordedTo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500, alias="pageSize"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    items, total = _metric_service.search_metrics(
        db,
        query=q,
        page=page,
        page_size=page_size,
        metric_scope=metric_scope,
        metric_name=metric_name,
        entity_type=entity_type,
        entity_id=entity_id,
        recorded_from=recorded_from,
        recorded_to=recorded_to,
    )
    return paginated([_serialize_metric(m) for m in items], page, page_size, total)


@router.post("", status_code=201, response_model=None, summary="Record a metric")
def create_metric(
    payload: AnalyticsMetricCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    metric = _metric_service.record_metric(
        db,
        metric_name=payload.metricName,
        metric_scope=payload.metricScope,
        metric_value=payload.metricValue,
        recorded_at=payload.recordedAt,
        entity_type=payload.entityType,
        entity_id=payload.entityId,
        metric_unit=payload.metricUnit,
        metadata=dict(payload.metadata or {}),
    )
    audit.log(db, action="create", module="analytics_metric", actor_id=user.id,
              entity_id=str(metric.id),
              entity_label=f"{metric.metric_scope}:{metric.metric_name}")
    analytics_events.metric_created(db, metric, actor_id=user.id)
    return ok(_serialize_metric(metric))


@router.get("/{metric_id}", response_model=None, summary="Get metric")
def get_metric(
    metric_id: _uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    return ok(_serialize_metric(_metric_service.get_metric(db, metric_id)))


@router.patch("/{metric_id}", response_model=None, summary="Update metric")
def update_metric(
    metric_id: _uuid.UUID,
    payload: AnalyticsMetricUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    metric = _metric_service.update_metric(
        db,
        metric_id,
        metric_value=payload.metricValue,
        metric_unit=payload.metricUnit,
        metadata=payload.metadata,
    )
    audit.log(db, action="update", module="analytics_metric", actor_id=user.id,
              entity_id=str(metric.id),
              entity_label=f"{metric.metric_scope}:{metric.metric_name}")
    analytics_events.metric_updated(db, metric, actor_id=user.id)
    return ok(_serialize_metric(metric))


@router.delete("/{metric_id}", response_model=None, summary="Delete metric")
def delete_metric(
    metric_id: _uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("analytics:manage")),
):
    metric = _metric_service.get_metric(db, metric_id)
    analytics_events.metric_deleted(db, metric, actor_id=user.id)
    _metric_service.delete_metric(db, metric_id)
    audit.log(db, action="delete", module="analytics_metric", actor_id=user.id,
              entity_id=str(metric_id))
    return ok({"deleted": True, "id": str(metric_id)})
