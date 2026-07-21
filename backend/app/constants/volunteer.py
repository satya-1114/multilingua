"""Centralized volunteer & task enums / state-machine constants.

The Pydantic schemas in :mod:`app.schemas.volunteer` narrow request/response
bodies with ``Literal`` types; these tuples are the single source of truth
those literals mirror. Import from here inside the service / repository /
router layers instead of re-declaring string literals.
"""
from __future__ import annotations

from typing import Final


# -- Volunteer ----------------------------------------------------------------

VOLUNTEER_STATUS_AVAILABLE: Final = "available"
VOLUNTEER_STATUS_BUSY: Final = "busy"
VOLUNTEER_STATUS_ON_LEAVE: Final = "on_leave"
VOLUNTEER_STATUS_INACTIVE: Final = "inactive"

VOLUNTEER_STATUSES: Final[tuple[str, ...]] = (
    VOLUNTEER_STATUS_AVAILABLE,
    VOLUNTEER_STATUS_BUSY,
    VOLUNTEER_STATUS_ON_LEAVE,
    VOLUNTEER_STATUS_INACTIVE,
)

VOLUNTEER_STATUSES_ACTIVE: Final[tuple[str, ...]] = (
    VOLUNTEER_STATUS_AVAILABLE,
    VOLUNTEER_STATUS_BUSY,
    VOLUNTEER_STATUS_ON_LEAVE,
)


# -- Task priority ------------------------------------------------------------

TASK_PRIORITY_LOW: Final = "low"
TASK_PRIORITY_MEDIUM: Final = "medium"
TASK_PRIORITY_HIGH: Final = "high"
TASK_PRIORITY_URGENT: Final = "urgent"

TASK_PRIORITIES: Final[tuple[str, ...]] = (
    TASK_PRIORITY_LOW,
    TASK_PRIORITY_MEDIUM,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_URGENT,
)


# -- Task status --------------------------------------------------------------

TASK_STATUS_PENDING: Final = "pending"
TASK_STATUS_ACCEPTED: Final = "accepted"
TASK_STATUS_IN_PROGRESS: Final = "in_progress"
TASK_STATUS_COMPLETED: Final = "completed"
TASK_STATUS_REJECTED: Final = "rejected"
TASK_STATUS_CANCELLED: Final = "cancelled"

TASK_STATUSES: Final[tuple[str, ...]] = (
    TASK_STATUS_PENDING,
    TASK_STATUS_ACCEPTED,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_REJECTED,
    TASK_STATUS_CANCELLED,
)

TASK_STATUSES_TERMINAL: Final[tuple[str, ...]] = (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_REJECTED,
    TASK_STATUS_CANCELLED,
)

# Legal transitions initiated by the assignee (task:act).
TASK_TRANSITIONS_ACTOR: Final[dict[str, tuple[str, ...]]] = {
    TASK_STATUS_PENDING: (TASK_STATUS_ACCEPTED, TASK_STATUS_REJECTED),
    TASK_STATUS_ACCEPTED: (TASK_STATUS_IN_PROGRESS,),
    TASK_STATUS_IN_PROGRESS: (TASK_STATUS_COMPLETED,),
}

# Legal transitions initiated by a manager (task:manage) — a superset that
# also lets managers force-cancel or reset when correcting mistakes.
TASK_TRANSITIONS_MANAGER: Final[dict[str, tuple[str, ...]]] = {
    TASK_STATUS_PENDING: (
        TASK_STATUS_ACCEPTED,
        TASK_STATUS_REJECTED,
        TASK_STATUS_CANCELLED,
    ),
    TASK_STATUS_ACCEPTED: (
        TASK_STATUS_IN_PROGRESS,
        TASK_STATUS_CANCELLED,
        TASK_STATUS_PENDING,
    ),
    TASK_STATUS_IN_PROGRESS: (
        TASK_STATUS_COMPLETED,
        TASK_STATUS_CANCELLED,
    ),
}


__all__ = [
    "VOLUNTEER_STATUS_AVAILABLE",
    "VOLUNTEER_STATUS_BUSY",
    "VOLUNTEER_STATUS_ON_LEAVE",
    "VOLUNTEER_STATUS_INACTIVE",
    "VOLUNTEER_STATUSES",
    "VOLUNTEER_STATUSES_ACTIVE",
    "TASK_PRIORITY_LOW",
    "TASK_PRIORITY_MEDIUM",
    "TASK_PRIORITY_HIGH",
    "TASK_PRIORITY_URGENT",
    "TASK_PRIORITIES",
    "TASK_STATUS_PENDING",
    "TASK_STATUS_ACCEPTED",
    "TASK_STATUS_IN_PROGRESS",
    "TASK_STATUS_COMPLETED",
    "TASK_STATUS_REJECTED",
    "TASK_STATUS_CANCELLED",
    "TASK_STATUSES",
    "TASK_STATUSES_TERMINAL",
    "TASK_TRANSITIONS_ACTOR",
    "TASK_TRANSITIONS_MANAGER",
]
