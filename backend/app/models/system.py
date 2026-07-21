from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class FeatureFlag(BaseMixin, Base):
    __tablename__ = "feature_flags"
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rollout_percent: Mapped[int] = mapped_column(Integer, default=0)
    scope: Mapped[str] = mapped_column(String(30), nullable=False, default="global")


class SystemConfiguration(BaseMixin, Base):
    __tablename__ = "system_configurations"
    section: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)


class License(BaseMixin, Base):
    __tablename__ = "licenses"
    plan: Mapped[str] = mapped_column(String(60), nullable=False)
    seats: Mapped[int] = mapped_column(Integer, default=0)
    seats_used: Mapped[int] = mapped_column(Integer, default=0)
    renews_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contract_id: Mapped[str] = mapped_column(String(80), nullable=False, default="")


class BackgroundJob(BaseMixin, Base):
    __tablename__ = "background_jobs"
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[dict] = mapped_column(JSONB, default=dict)


class HealthCheck(BaseMixin, Base):
    __tablename__ = "health_checks"
    component: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ok")
    latency_ms: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    detail: Mapped[str] = mapped_column(String(500), default="")


class MonitoringMetric(BaseMixin, Base):
    __tablename__ = "monitoring_metrics"
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    unit: Mapped[str] = mapped_column(String(30), nullable=False, default="ms")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
