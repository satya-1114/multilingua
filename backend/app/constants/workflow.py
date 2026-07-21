"""Automation & Workflow Engine enums / constants (Phase 7.1).

Single source of truth for workflow-related enum literals. Pydantic
schemas in :mod:`app.schemas.workflow` mirror these via ``Literal``
types.
"""
from __future__ import annotations

from typing import Final


# -- Trigger type -------------------------------------------------------------

TRIGGER_TYPE_EVENT: Final = "event"
TRIGGER_TYPE_SCHEDULE: Final = "schedule"
TRIGGER_TYPE_MANUAL: Final = "manual"

TRIGGER_TYPES: Final[tuple[str, ...]] = (
    TRIGGER_TYPE_EVENT,
    TRIGGER_TYPE_SCHEDULE,
    TRIGGER_TYPE_MANUAL,
)


# -- Workflow execution status -----------------------------------------------

WORKFLOW_STATUS_PENDING: Final = "pending"
WORKFLOW_STATUS_RUNNING: Final = "running"
WORKFLOW_STATUS_COMPLETED: Final = "completed"
WORKFLOW_STATUS_FAILED: Final = "failed"
WORKFLOW_STATUS_CANCELLED: Final = "cancelled"

WORKFLOW_STATUSES: Final[tuple[str, ...]] = (
    WORKFLOW_STATUS_PENDING,
    WORKFLOW_STATUS_RUNNING,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_CANCELLED,
)


# -- Step status --------------------------------------------------------------

STEP_STATUS_PENDING: Final = "pending"
STEP_STATUS_RUNNING: Final = "running"
STEP_STATUS_COMPLETED: Final = "completed"
STEP_STATUS_FAILED: Final = "failed"
STEP_STATUS_SKIPPED: Final = "skipped"

STEP_STATUSES: Final[tuple[str, ...]] = (
    STEP_STATUS_PENDING,
    STEP_STATUS_RUNNING,
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
    STEP_STATUS_SKIPPED,
)


# -- Action type --------------------------------------------------------------

ACTION_TYPE_NOTIFICATION: Final = "notification"
ACTION_TYPE_AUDIT: Final = "audit"
ACTION_TYPE_ANALYTICS: Final = "analytics"
ACTION_TYPE_WEBHOOK: Final = "webhook"
ACTION_TYPE_EMAIL: Final = "email"
ACTION_TYPE_SMS: Final = "sms"
ACTION_TYPE_UPDATE_ENTITY: Final = "update_entity"
ACTION_TYPE_CUSTOM: Final = "custom"

ACTION_TYPES: Final[tuple[str, ...]] = (
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_AUDIT,
    ACTION_TYPE_ANALYTICS,
    ACTION_TYPE_WEBHOOK,
    ACTION_TYPE_EMAIL,
    ACTION_TYPE_SMS,
    ACTION_TYPE_UPDATE_ENTITY,
    ACTION_TYPE_CUSTOM,
)


__all__ = [
    "TRIGGER_TYPE_EVENT",
    "TRIGGER_TYPE_SCHEDULE",
    "TRIGGER_TYPE_MANUAL",
    "TRIGGER_TYPES",
    "WORKFLOW_STATUS_PENDING",
    "WORKFLOW_STATUS_RUNNING",
    "WORKFLOW_STATUS_COMPLETED",
    "WORKFLOW_STATUS_FAILED",
    "WORKFLOW_STATUS_CANCELLED",
    "WORKFLOW_STATUSES",
    "STEP_STATUS_PENDING",
    "STEP_STATUS_RUNNING",
    "STEP_STATUS_COMPLETED",
    "STEP_STATUS_FAILED",
    "STEP_STATUS_SKIPPED",
    "STEP_STATUSES",
    "ACTION_TYPE_NOTIFICATION",
    "ACTION_TYPE_AUDIT",
    "ACTION_TYPE_ANALYTICS",
    "ACTION_TYPE_WEBHOOK",
    "ACTION_TYPE_EMAIL",
    "ACTION_TYPE_SMS",
    "ACTION_TYPE_UPDATE_ENTITY",
    "ACTION_TYPE_CUSTOM",
    "ACTION_TYPES",
]
