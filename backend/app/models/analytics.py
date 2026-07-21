"""Analytics & Reporting platform ORM models (Phase 6.1 — DB foundation).

Generic, module-agnostic persistence for platform-wide analytics:

* ``AnalyticsMetric``  — polymorphic time-series metric points.
* ``AnalyticsSnapshot`` — aggregated KPI snapshots per period.
* ``AnalyticsReport``  — tracked report-generation jobs.

Entity references are polymorphic (``entity_type`` + ``entity_id``) so
future modules require zero schema changes. The legacy ``Report`` model
(user-defined reports on ``reports``) is preserved unchanged for
backwards compatibility.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


# --------------------------------------------------------------------------- #
# Legacy user-defined reports (unchanged — preserved for compatibility).
# --------------------------------------------------------------------------- #


class Report(BaseMixin, Base):
    __tablename__ = "reports"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)


# --------------------------------------------------------------------------- #
# Analytics platform (Phase 6.1).
# --------------------------------------------------------------------------- #


class AnalyticsMetric(BaseMixin, Base):
    """Polymorphic time-series metric point.

    ``entity_type`` + ``entity_id`` reference any domain entity; no
    foreign keys are declared so new modules can emit metrics without
    schema changes.
    """

    __tablename__ = "analytics_metrics"

    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_scope: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metric_value: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False, default=0)
    metric_unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    __table_args__ = (
        Index("ix_analytics_metrics_scope", "metric_scope"),
        Index("ix_analytics_metrics_entity", "entity_type", "entity_id"),
        Index("ix_analytics_metrics_name", "metric_name"),
        Index("ix_analytics_metrics_recorded_at", "recorded_at"),
    )


class AnalyticsSnapshot(BaseMixin, Base):
    """Aggregated KPI snapshot for a period (daily/weekly/monthly/custom)."""

    __tablename__ = "analytics_snapshots"

    snapshot_type: Mapped[str] = mapped_column(String(20), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    metrics_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    # Polymorphic organization reference is expressed as FK only; no ORM relationship.

    __table_args__ = (
        Index("ix_analytics_snapshots_type", "snapshot_type"),
        Index("ix_analytics_snapshots_period", "period_start", "period_end"),
    )


class AnalyticsReport(BaseMixin, Base):
    """Tracks an analytics report generation job."""

    __tablename__ = "analytics_reports"

    report_name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    # FK-only linkage; services join explicitly when needed.

    __table_args__ = (
        Index("ix_analytics_reports_status", "status"),
        Index("ix_analytics_reports_generated_at", "generated_at"),
    )
