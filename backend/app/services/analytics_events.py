"""Analytics platform domain-event emitters (Phase 6.4).

Thin adapter that translates AnalyticsMetric / AnalyticsSnapshot /
AnalyticsReport business events into the existing
:mod:`app.services.notifications` pipeline. Kept isolated from the core
service so business logic stays pure and testable.

All emitters swallow errors: a notification failure MUST NOT abort the
underlying business operation. Errors are logged only.
"""
from __future__ import annotations

import uuid
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.analytics import AnalyticsMetric, AnalyticsReport, AnalyticsSnapshot
from app.runtime.events import publish_event
from app.services import notifications as notif_service

log = get_logger(__name__)

CATEGORY = "analytics"


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #


def _safe_create(db: Session, *, user_id: uuid.UUID | str | None, **kwargs: Any) -> None:
    if user_id is None:
        return
    if not isinstance(user_id, uuid.UUID):
        try:
            user_id = uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            return
    try:
        notif_service.create(db, user_id=user_id, category=CATEGORY, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("analytics notification emit failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


def _broadcast(
    db: Session,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None,
    *,
    title: str,
    message: str,
    priority: str = "low",
    href: str = "/analytics",
) -> None:
    seen: set[str] = set()
    for uid in notify_user_ids or ():
        if uid is None:
            continue
        key = str(uid)
        if key in seen:
            continue
        seen.add(key)
        _safe_create(db, user_id=uid, title=title, message=message,
                     priority=priority, href=href)


# --------------------------------------------------------------------------- #
# Metric lifecycle
# --------------------------------------------------------------------------- #


def _metric_href(m: AnalyticsMetric) -> str:
    return f"/analytics/metrics/{m.id}"


def _metric_label(m: AnalyticsMetric) -> str:
    return f"{m.metric_scope}:{m.metric_name}"


def metric_created(
    db: Session,
    m: AnalyticsMetric,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title=f"Metric recorded: {_metric_label(m)}",
        message="A new analytics metric point has been recorded.",
        href=_metric_href(m),
    )
    publish_event(
        "analytics.metric.created",
        db=db,
        actor_id=actor_id,
        resource_type="analytics_metric",
        resource_id=m.id,
        payload={"metricName": m.metric_name, "metricScope": m.metric_scope},
    )


def metric_updated(
    db: Session,
    m: AnalyticsMetric,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title=f"Metric updated: {_metric_label(m)}",
        message="An analytics metric has been updated.",
        href=_metric_href(m),
    )


def metric_deleted(
    db: Session,
    m: AnalyticsMetric,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title=f"Metric deleted: {_metric_label(m)}",
        message="An analytics metric has been deleted.",
        href="/analytics",
    )


# --------------------------------------------------------------------------- #
# Snapshot lifecycle
# --------------------------------------------------------------------------- #


def _snapshot_href(s: AnalyticsSnapshot) -> str:
    return f"/analytics/snapshots/{s.id}"


def _snapshot_label(s: AnalyticsSnapshot) -> str:
    return f"{s.snapshot_type} snapshot"


def snapshot_created(
    db: Session,
    s: AnalyticsSnapshot,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title=f"Snapshot generated: {_snapshot_label(s)}",
        message="An analytics snapshot has been generated.",
        href=_snapshot_href(s),
    )


def snapshot_regenerated(
    db: Session,
    s: AnalyticsSnapshot,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title=f"Snapshot regenerated: {_snapshot_label(s)}",
        message="An analytics snapshot has been regenerated.",
        priority="normal",
        href=_snapshot_href(s),
    )


def snapshot_deleted(
    db: Session,
    s: AnalyticsSnapshot,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title=f"Snapshot deleted: {_snapshot_label(s)}",
        message="An analytics snapshot has been deleted.",
        href="/analytics/snapshots",
    )


# --------------------------------------------------------------------------- #
# Report lifecycle
# --------------------------------------------------------------------------- #


def _report_href(r: AnalyticsReport) -> str:
    return f"/analytics/reports/{r.id}"


def _report_recipients(
    r: AnalyticsReport,
    actor_id: uuid.UUID | str | None,
    extra: Iterable[uuid.UUID | str | None] | None,
) -> list[uuid.UUID | str | None]:
    out: list[uuid.UUID | str | None] = []
    for uid in (r.requested_by_user_id, actor_id, *(extra or ())):
        if uid is not None:
            out.append(uid)
    return out


def report_requested(
    db: Session,
    r: AnalyticsReport,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, _report_recipients(r, actor_id, notify_user_ids),
        title=f"Report requested: {r.report_name}",
        message="Your report has been queued for generation.",
        href=_report_href(r),
    )


def report_generation_started(
    db: Session,
    r: AnalyticsReport,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, _report_recipients(r, actor_id, notify_user_ids),
        title=f"Report generating: {r.report_name}",
        message="Your report is now being generated.",
        href=_report_href(r),
    )


def report_generation_completed(
    db: Session,
    r: AnalyticsReport,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, _report_recipients(r, actor_id, notify_user_ids),
        title=f"Report ready: {r.report_name}",
        message="Your report has been generated and is available for download.",
        priority="normal",
        href=_report_href(r),
    )
    publish_event(
        "analytics.report.completed",
        db=db,
        actor_id=actor_id,
        resource_type="analytics_report",
        resource_id=r.id,
        payload={"reportName": r.report_name, "format": getattr(r, "format", None)},
    )


def report_generation_failed(
    db: Session,
    r: AnalyticsReport,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, _report_recipients(r, actor_id, notify_user_ids),
        title=f"Report failed: {r.report_name}",
        message="Report generation failed. See report details for the error.",
        priority="high",
        href=_report_href(r),
    )


def report_expired(
    db: Session,
    r: AnalyticsReport,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, _report_recipients(r, actor_id, notify_user_ids),
        title=f"Report expired: {r.report_name}",
        message="This report has expired and is no longer available for download.",
        href=_report_href(r),
    )


def report_deleted(
    db: Session,
    r: AnalyticsReport,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, _report_recipients(r, actor_id, notify_user_ids),
        title=f"Report deleted: {r.report_name}",
        message="An analytics report has been deleted.",
        href="/analytics/reports",
    )


__all__ = [
    "CATEGORY",
    "metric_created",
    "metric_updated",
    "metric_deleted",
    "snapshot_created",
    "snapshot_regenerated",
    "snapshot_deleted",
    "report_requested",
    "report_generation_started",
    "report_generation_completed",
    "report_generation_failed",
    "report_expired",
    "report_deleted",
]
