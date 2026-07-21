"""Pydantic schemas for the Analytics & Reporting platform (Phase 6.1).

Legacy KPI/report DTOs used by the existing analytics service are
preserved. New DTOs power the AnalyticsMetric / AnalyticsSnapshot /
AnalyticsReport tables and mirror :mod:`app.constants.analytics`.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import IdentifiedDto


# -- Legacy analytics DTOs (unchanged) ---------------------------------------


class AnalyticsKpiDto(BaseModel):
    key: str
    label: str
    value: float
    delta: float | None = None
    unit: str | None = None


class ReportDto(IdentifiedDto):
    name: str
    kind: str
    scheduled: bool = False


# -- Enum literals (mirror app.constants.analytics) --------------------------

MetricScope = Literal[
    "volunteer",
    "disaster",
    "public_resource",
    "translation",
    "organization",
    "platform",
]
ReportStatus = Literal["pending", "generating", "completed", "failed"]
SnapshotType = Literal["daily", "weekly", "monthly", "custom"]


# --------------------------------------------------------------------------- #
# AnalyticsMetric
# --------------------------------------------------------------------------- #


class AnalyticsMetricBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    metricName: str = Field(alias="metric_name", min_length=1, max_length=120)
    metricScope: MetricScope = Field(alias="metric_scope")
    entityType: str | None = Field(alias="entity_type", default=None, max_length=40)
    entityId: uuid.UUID | None = Field(alias="entity_id", default=None)
    metricValue: float = Field(alias="metric_value", default=0.0)
    metricUnit: str | None = Field(alias="metric_unit", default=None, max_length=40)


class AnalyticsMetricCreate(AnalyticsMetricBase):
    recordedAt: datetime = Field(alias="recorded_at")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsMetricUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    metricValue: float | None = Field(alias="metric_value", default=None)
    metricUnit: str | None = Field(alias="metric_unit", default=None, max_length=40)
    metadata: dict[str, Any] | None = None


class AnalyticsMetricDto(IdentifiedDto):
    metricName: str = Field(alias="metric_name")
    metricScope: MetricScope = Field(alias="metric_scope")
    entityType: str | None = Field(alias="entity_type", default=None)
    entityId: uuid.UUID | None = Field(alias="entity_id", default=None)
    metricValue: float = Field(alias="metric_value")
    metricUnit: str | None = Field(alias="metric_unit", default=None)
    recordedAt: datetime = Field(alias="recorded_at")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsMetricListQuery(BaseModel):
    metricScope: MetricScope | None = None
    metricName: str | None = None
    entityType: str | None = None
    entityId: uuid.UUID | None = None
    recordedFrom: datetime | None = None
    recordedTo: datetime | None = None
    page: int = 1
    pageSize: int = 50


# --------------------------------------------------------------------------- #
# AnalyticsSnapshot
# --------------------------------------------------------------------------- #


class AnalyticsSnapshotBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    snapshotType: SnapshotType = Field(alias="snapshot_type")
    organizationId: uuid.UUID | None = Field(alias="organization_id", default=None)
    periodStart: datetime = Field(alias="period_start")
    periodEnd: datetime = Field(alias="period_end")

    @model_validator(mode="after")
    def _validate_period(self):
        if self.periodEnd < self.periodStart:
            raise ValueError("period_end must be >= period_start")
        return self


class AnalyticsSnapshotCreate(AnalyticsSnapshotBase):
    generatedAt: datetime = Field(alias="generated_at")
    metricsJson: dict[str, Any] = Field(alias="metrics_json", default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsSnapshotUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    metricsJson: dict[str, Any] | None = Field(alias="metrics_json", default=None)
    metadata: dict[str, Any] | None = None


class AnalyticsSnapshotDto(IdentifiedDto):
    snapshotType: SnapshotType = Field(alias="snapshot_type")
    organizationId: uuid.UUID | None = Field(alias="organization_id", default=None)
    periodStart: datetime = Field(alias="period_start")
    periodEnd: datetime = Field(alias="period_end")
    generatedAt: datetime = Field(alias="generated_at")
    metricsJson: dict[str, Any] = Field(alias="metrics_json", default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# AnalyticsReport
# --------------------------------------------------------------------------- #


class AnalyticsReportBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reportName: str = Field(alias="report_name", min_length=1, max_length=200)
    reportType: str = Field(alias="report_type", min_length=1, max_length=40)
    organizationId: uuid.UUID | None = Field(alias="organization_id", default=None)


class AnalyticsReportCreate(AnalyticsReportBase):
    requestedByUserId: uuid.UUID | None = Field(
        alias="requested_by_user_id", default=None
    )
    status: ReportStatus = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsReportUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: ReportStatus | None = None
    filePath: str | None = Field(alias="file_path", default=None, max_length=500)
    generatedAt: datetime | None = Field(alias="generated_at", default=None)
    expiresAt: datetime | None = Field(alias="expires_at", default=None)
    metadata: dict[str, Any] | None = None


class AnalyticsReportDto(IdentifiedDto):
    reportName: str = Field(alias="report_name")
    reportType: str = Field(alias="report_type")
    requestedByUserId: uuid.UUID | None = Field(
        alias="requested_by_user_id", default=None
    )
    organizationId: uuid.UUID | None = Field(alias="organization_id", default=None)
    status: ReportStatus
    filePath: str | None = Field(alias="file_path", default=None)
    generatedAt: datetime | None = Field(alias="generated_at", default=None)
    expiresAt: datetime | None = Field(alias="expires_at", default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsReportListQuery(BaseModel):
    status: ReportStatus | None = None
    reportType: str | None = None
    organizationId: uuid.UUID | None = None
    requestedByUserId: uuid.UUID | None = None
    generatedFrom: datetime | None = None
    generatedTo: datetime | None = None
    page: int = 1
    pageSize: int = 50


class AnalyticsSearchQuery(BaseModel):
    """Free-text search across analytics reports / snapshots."""

    q: str | None = None
    metricScope: MetricScope | None = None
    snapshotType: SnapshotType | None = None
    reportStatus: ReportStatus | None = None
    page: int = 1
    pageSize: int = 50
