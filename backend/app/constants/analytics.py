"""Analytics & Reporting platform enums / constants (Phase 6.1).

Single source of truth for analytics-related enum literals. Pydantic
schemas in :mod:`app.schemas.analytics` mirror these via ``Literal``
types. Reusable across every module — future modules require no
schema changes to be tracked here.
"""
from __future__ import annotations

from typing import Final


# -- Metric scope -------------------------------------------------------------

METRIC_SCOPE_VOLUNTEER: Final = "volunteer"
METRIC_SCOPE_DISASTER: Final = "disaster"
METRIC_SCOPE_PUBLIC_RESOURCE: Final = "public_resource"
METRIC_SCOPE_TRANSLATION: Final = "translation"
METRIC_SCOPE_ORGANIZATION: Final = "organization"
METRIC_SCOPE_PLATFORM: Final = "platform"

METRIC_SCOPES: Final[tuple[str, ...]] = (
    METRIC_SCOPE_VOLUNTEER,
    METRIC_SCOPE_DISASTER,
    METRIC_SCOPE_PUBLIC_RESOURCE,
    METRIC_SCOPE_TRANSLATION,
    METRIC_SCOPE_ORGANIZATION,
    METRIC_SCOPE_PLATFORM,
)


# -- Report status ------------------------------------------------------------

REPORT_STATUS_PENDING: Final = "pending"
REPORT_STATUS_GENERATING: Final = "generating"
REPORT_STATUS_COMPLETED: Final = "completed"
REPORT_STATUS_FAILED: Final = "failed"

REPORT_STATUSES: Final[tuple[str, ...]] = (
    REPORT_STATUS_PENDING,
    REPORT_STATUS_GENERATING,
    REPORT_STATUS_COMPLETED,
    REPORT_STATUS_FAILED,
)


# -- Snapshot type ------------------------------------------------------------

SNAPSHOT_TYPE_DAILY: Final = "daily"
SNAPSHOT_TYPE_WEEKLY: Final = "weekly"
SNAPSHOT_TYPE_MONTHLY: Final = "monthly"
SNAPSHOT_TYPE_CUSTOM: Final = "custom"

SNAPSHOT_TYPES: Final[tuple[str, ...]] = (
    SNAPSHOT_TYPE_DAILY,
    SNAPSHOT_TYPE_WEEKLY,
    SNAPSHOT_TYPE_MONTHLY,
    SNAPSHOT_TYPE_CUSTOM,
)


__all__ = [
    "METRIC_SCOPE_VOLUNTEER",
    "METRIC_SCOPE_DISASTER",
    "METRIC_SCOPE_PUBLIC_RESOURCE",
    "METRIC_SCOPE_TRANSLATION",
    "METRIC_SCOPE_ORGANIZATION",
    "METRIC_SCOPE_PLATFORM",
    "METRIC_SCOPES",
    "REPORT_STATUS_PENDING",
    "REPORT_STATUS_GENERATING",
    "REPORT_STATUS_COMPLETED",
    "REPORT_STATUS_FAILED",
    "REPORT_STATUSES",
    "SNAPSHOT_TYPE_DAILY",
    "SNAPSHOT_TYPE_WEEKLY",
    "SNAPSHOT_TYPE_MONTHLY",
    "SNAPSHOT_TYPE_CUSTOM",
    "SNAPSHOT_TYPES",
]
