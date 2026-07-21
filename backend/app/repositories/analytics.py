"""Repository layer for the Analytics & Reporting platform (Phase 6.2).

Thin extensions over :class:`CRUDBase`. All business rules — workflow
transitions, validation, aggregation orchestration — live in
:mod:`app.services.analytics`.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.analytics import (
    AnalyticsMetric,
    AnalyticsReport,
    AnalyticsSnapshot,
)


# --------------------------------------------------------------------------- #
# AnalyticsMetric
# --------------------------------------------------------------------------- #


class AnalyticsMetricRepository(CRUDBase[AnalyticsMetric]):
    def __init__(self) -> None:
        super().__init__(AnalyticsMetric)

    def create_metric(self, db: Session, data: dict[str, Any]) -> AnalyticsMetric:
        return self.create(db, data)

    def get_metric(self, db: Session, metric_id: uuid.UUID | str) -> AnalyticsMetric | None:
        return self.get(db, metric_id)

    def list_metrics(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        metric_scope: str | None = None,
        metric_name: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | str | None = None,
        recorded_from: datetime | None = None,
        recorded_to: datetime | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[AnalyticsMetric], int]:
        stmt = select(AnalyticsMetric).where(AnalyticsMetric.deleted_at.is_(None))
        if metric_scope:
            stmt = stmt.where(AnalyticsMetric.metric_scope == metric_scope)
        if metric_name:
            stmt = stmt.where(AnalyticsMetric.metric_name == metric_name)
        if entity_type:
            stmt = stmt.where(AnalyticsMetric.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AnalyticsMetric.entity_id == entity_id)
        if recorded_from:
            stmt = stmt.where(AnalyticsMetric.recorded_at >= recorded_from)
        if recorded_to:
            stmt = stmt.where(AnalyticsMetric.recorded_at <= recorded_to)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(AnalyticsMetric, sort_by):
            col = getattr(AnalyticsMetric, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(AnalyticsMetric.recorded_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def search_metrics(
        self,
        db: Session,
        *,
        query: str | None = None,
        page: int = 1,
        page_size: int = 50,
        **filters: Any,
    ) -> tuple[list[AnalyticsMetric], int]:
        items, total = self.list_metrics(db, page=1, page_size=10_000, **filters)
        if query:
            q = query.lower()
            items = [
                m for m in items
                if q in (m.metric_name or "").lower()
                or q in (m.entity_type or "").lower()
                or q in (m.metric_unit or "").lower()
            ]
            total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def delete_metric(self, db: Session, obj: AnalyticsMetric) -> None:
        self.soft_delete(db, obj)

    def aggregate_metrics(
        self,
        db: Session,
        *,
        metric_name: str,
        metric_scope: str | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | str | None = None,
        recorded_from: datetime | None = None,
        recorded_to: datetime | None = None,
    ) -> dict[str, float]:
        stmt = select(
            func.count(AnalyticsMetric.id),
            func.coalesce(func.sum(AnalyticsMetric.metric_value), 0),
            func.coalesce(func.avg(AnalyticsMetric.metric_value), 0),
            func.coalesce(func.min(AnalyticsMetric.metric_value), 0),
            func.coalesce(func.max(AnalyticsMetric.metric_value), 0),
        ).where(
            AnalyticsMetric.deleted_at.is_(None),
            AnalyticsMetric.metric_name == metric_name,
        )
        if metric_scope:
            stmt = stmt.where(AnalyticsMetric.metric_scope == metric_scope)
        if entity_type:
            stmt = stmt.where(AnalyticsMetric.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AnalyticsMetric.entity_id == entity_id)
        if recorded_from:
            stmt = stmt.where(AnalyticsMetric.recorded_at >= recorded_from)
        if recorded_to:
            stmt = stmt.where(AnalyticsMetric.recorded_at <= recorded_to)
        count, total, avg, mn, mx = db.execute(stmt).one()
        return {
            "count": int(count or 0),
            "sum": float(total or 0),
            "avg": float(avg or 0),
            "min": float(mn or 0),
            "max": float(mx or 0),
        }


# --------------------------------------------------------------------------- #
# AnalyticsSnapshot
# --------------------------------------------------------------------------- #


class AnalyticsSnapshotRepository(CRUDBase[AnalyticsSnapshot]):
    def __init__(self) -> None:
        super().__init__(AnalyticsSnapshot)

    def create_snapshot(self, db: Session, data: dict[str, Any]) -> AnalyticsSnapshot:
        return self.create(db, data)

    def get_snapshot(self, db: Session, snapshot_id: uuid.UUID | str) -> AnalyticsSnapshot | None:
        return self.get(db, snapshot_id)

    def find_existing(
        self,
        db: Session,
        *,
        snapshot_type: str,
        period_start: datetime,
        period_end: datetime,
        organization_id: uuid.UUID | str | None = None,
    ) -> AnalyticsSnapshot | None:
        stmt = select(AnalyticsSnapshot).where(
            AnalyticsSnapshot.deleted_at.is_(None),
            AnalyticsSnapshot.snapshot_type == snapshot_type,
            AnalyticsSnapshot.period_start == period_start,
            AnalyticsSnapshot.period_end == period_end,
        )
        if organization_id is None:
            stmt = stmt.where(AnalyticsSnapshot.organization_id.is_(None))
        else:
            stmt = stmt.where(AnalyticsSnapshot.organization_id == organization_id)
        return db.scalar(stmt)

    def list_snapshots(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        snapshot_type: str | None = None,
        organization_id: uuid.UUID | str | None = None,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[AnalyticsSnapshot], int]:
        stmt = select(AnalyticsSnapshot).where(AnalyticsSnapshot.deleted_at.is_(None))
        if snapshot_type:
            stmt = stmt.where(AnalyticsSnapshot.snapshot_type == snapshot_type)
        if organization_id:
            stmt = stmt.where(AnalyticsSnapshot.organization_id == organization_id)
        if period_from:
            stmt = stmt.where(AnalyticsSnapshot.period_start >= period_from)
        if period_to:
            stmt = stmt.where(AnalyticsSnapshot.period_end <= period_to)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(AnalyticsSnapshot, sort_by):
            col = getattr(AnalyticsSnapshot, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(AnalyticsSnapshot.period_start.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def latest_snapshot(
        self,
        db: Session,
        *,
        snapshot_type: str,
        organization_id: uuid.UUID | str | None = None,
    ) -> AnalyticsSnapshot | None:
        stmt = select(AnalyticsSnapshot).where(
            AnalyticsSnapshot.deleted_at.is_(None),
            AnalyticsSnapshot.snapshot_type == snapshot_type,
        )
        if organization_id is not None:
            stmt = stmt.where(AnalyticsSnapshot.organization_id == organization_id)
        stmt = stmt.order_by(AnalyticsSnapshot.period_start.desc()).limit(1)
        return db.scalar(stmt)

    def update_snapshot(
        self, db: Session, obj: AnalyticsSnapshot, data: dict[str, Any]
    ) -> AnalyticsSnapshot:
        return self.update(db, obj, data)

    def delete_snapshot(self, db: Session, obj: AnalyticsSnapshot) -> None:
        self.soft_delete(db, obj)


# --------------------------------------------------------------------------- #
# AnalyticsReport
# --------------------------------------------------------------------------- #


class AnalyticsReportRepository(CRUDBase[AnalyticsReport]):
    def __init__(self) -> None:
        super().__init__(AnalyticsReport)

    def create_report(self, db: Session, data: dict[str, Any]) -> AnalyticsReport:
        return self.create(db, data)

    def get_report(self, db: Session, report_id: uuid.UUID | str) -> AnalyticsReport | None:
        return self.get(db, report_id)

    def list_reports(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        report_type: str | None = None,
        organization_id: uuid.UUID | str | None = None,
        requested_by_user_id: uuid.UUID | str | None = None,
        generated_from: datetime | None = None,
        generated_to: datetime | None = None,
        query: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[AnalyticsReport], int]:
        stmt = select(AnalyticsReport).where(AnalyticsReport.deleted_at.is_(None))
        if status:
            stmt = stmt.where(AnalyticsReport.status == status)
        if report_type:
            stmt = stmt.where(AnalyticsReport.report_type == report_type)
        if organization_id:
            stmt = stmt.where(AnalyticsReport.organization_id == organization_id)
        if requested_by_user_id:
            stmt = stmt.where(
                AnalyticsReport.requested_by_user_id == requested_by_user_id
            )
        if generated_from:
            stmt = stmt.where(AnalyticsReport.generated_at >= generated_from)
        if generated_to:
            stmt = stmt.where(AnalyticsReport.generated_at <= generated_to)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    AnalyticsReport.report_name.ilike(like),
                    AnalyticsReport.report_type.ilike(like),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(AnalyticsReport, sort_by):
            col = getattr(AnalyticsReport, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(AnalyticsReport.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def update_report(
        self, db: Session, obj: AnalyticsReport, data: dict[str, Any]
    ) -> AnalyticsReport:
        return self.update(db, obj, data)

    def delete_report(self, db: Session, obj: AnalyticsReport) -> None:
        self.soft_delete(db, obj)


# --------------------------------------------------------------------------- #
# Module-level singletons — mirrors the pattern used by other repositories.
# --------------------------------------------------------------------------- #

analytics_metrics = AnalyticsMetricRepository()
analytics_snapshots = AnalyticsSnapshotRepository()
analytics_reports = AnalyticsReportRepository()


__all__ = [
    "AnalyticsMetricRepository",
    "AnalyticsSnapshotRepository",
    "AnalyticsReportRepository",
    "analytics_metrics",
    "analytics_snapshots",
    "analytics_reports",
]
