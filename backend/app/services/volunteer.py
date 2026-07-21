"""Volunteer & Volunteer-Task business services.

Pure business layer: input validation, state-machine enforcement, and
permission checks. No HTTP / FastAPI code lives here — routers translate
DTOs, call these functions, and serialize the result.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.constants.volunteer import (
    TASK_PRIORITIES,
    TASK_PRIORITY_MEDIUM,
    TASK_STATUS_ACCEPTED,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_PENDING,
    TASK_STATUS_REJECTED,
    TASK_STATUSES,
    TASK_STATUSES_TERMINAL,
    TASK_TRANSITIONS_ACTOR,
    TASK_TRANSITIONS_MANAGER,
    VOLUNTEER_STATUS_AVAILABLE,
    VOLUNTEER_STATUS_INACTIVE,
    VOLUNTEER_STATUSES,
)
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.models.volunteer import Volunteer, VolunteerTask
from app.repositories.volunteer import volunteer_tasks, volunteers
from app.security.rbac import require_permission
from app.services import volunteer_events as events


# ---------------------------------------------------------------------------
# Volunteer service
# ---------------------------------------------------------------------------


def _as_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Invalid UUID: {value!r}") from exc


def _get_volunteer_or_404(db: Session, volunteer_id: uuid.UUID | str) -> Volunteer:
    obj = volunteers.get(db, _as_uuid(volunteer_id))
    if obj is None:
        raise NotFoundError("Volunteer not found", details={"id": str(volunteer_id)})
    return obj


def _flatten_emergency(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize the nested ``emergencyContact`` DTO into flat columns."""
    contact = data.pop("emergencyContact", None) or data.pop("emergency_contact", None)
    if contact is None:
        return data
    if hasattr(contact, "model_dump"):
        contact = contact.model_dump()
    data["emergency_contact_name"] = contact.get("name")
    data["emergency_contact_phone"] = contact.get("phone")
    data["emergency_contact_relation"] = contact.get("relation")
    return data


def _normalize_volunteer_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _flatten_emergency(dict(payload))
    # DTO camelCase → column snake_case for the couple of fields that differ.
    aliases = {
        "userId": "user_id",
        "organizationId": "organization_id",
        "currentLocation": "current_location",
    }
    for src, dst in aliases.items():
        if src in payload:
            payload[dst] = payload.pop(src)
    return payload


def create_volunteer(
    db: Session,
    *,
    roles: Iterable[str],
    payload: dict[str, Any],
) -> Volunteer:
    require_permission(roles, "volunteer:manage")
    data = _normalize_volunteer_payload(payload)

    user_id = data.get("user_id")
    if not user_id:
        raise ValidationError("userId is required")

    existing = volunteers.get_by_user(db, user_id)
    if existing is not None:
        raise ConflictError(
            "Volunteer profile already exists for this user",
            details={"userId": str(user_id)},
        )

    status = data.get("status") or VOLUNTEER_STATUS_AVAILABLE
    if status not in VOLUNTEER_STATUSES:
        raise ValidationError(f"Invalid volunteer status: {status}")
    data["status"] = status
    data.setdefault("languages", [])
    data.setdefault("skills", [])
    return volunteers.create(db, data)


def update_volunteer(
    db: Session,
    *,
    roles: Iterable[str],
    volunteer_id: uuid.UUID | str,
    payload: dict[str, Any],
) -> Volunteer:
    require_permission(roles, "volunteer:manage")
    volunteer = _get_volunteer_or_404(db, volunteer_id)
    data = _normalize_volunteer_payload(payload)
    if "status" in data and data["status"] is not None:
        if data["status"] not in VOLUNTEER_STATUSES:
            raise ValidationError(f"Invalid volunteer status: {data['status']}")
    return volunteers.update(db, volunteer, data)


def set_status(
    db: Session,
    *,
    roles: Iterable[str],
    volunteer_id: uuid.UUID | str,
    status: str,
) -> Volunteer:
    require_permission(roles, "volunteer:manage")
    if status not in VOLUNTEER_STATUSES:
        raise ValidationError(f"Invalid volunteer status: {status}")
    volunteer = _get_volunteer_or_404(db, volunteer_id)
    previous_status = volunteer.status
    updated = volunteers.update(db, volunteer, {"status": status})
    if previous_status != status:
        if status == VOLUNTEER_STATUS_AVAILABLE:
            events.volunteer_activated(db, updated)
        elif status == VOLUNTEER_STATUS_INACTIVE:
            events.volunteer_deactivated(db, updated)
    return updated


def activate(db: Session, *, roles: Iterable[str], volunteer_id: uuid.UUID | str) -> Volunteer:
    return set_status(
        db, roles=roles, volunteer_id=volunteer_id, status=VOLUNTEER_STATUS_AVAILABLE
    )


def deactivate(
    db: Session, *, roles: Iterable[str], volunteer_id: uuid.UUID | str
) -> Volunteer:
    return set_status(
        db, roles=roles, volunteer_id=volunteer_id, status=VOLUNTEER_STATUS_INACTIVE
    )


def assign_organization(
    db: Session,
    *,
    roles: Iterable[str],
    volunteer_id: uuid.UUID | str,
    organization_id: uuid.UUID | str | None,
) -> Volunteer:
    require_permission(roles, "volunteer:manage")
    volunteer = _get_volunteer_or_404(db, volunteer_id)
    org: uuid.UUID | None
    if organization_id is None or organization_id == "":
        org = None
    elif isinstance(organization_id, uuid.UUID):
        org = organization_id
    else:
        try:
            org = uuid.UUID(str(organization_id))
        except (ValueError, TypeError) as exc:
            raise ValidationError("organizationId must be a valid UUID") from exc
    return volunteers.update(db, volunteer, {"organization_id": org})


def list_volunteers(
    db: Session,
    *,
    roles: Iterable[str],
    filters: dict[str, Any],
) -> tuple[list[Volunteer], int]:
    require_permission(roles, "volunteer:view")
    return volunteers.search(db, **filters)


def get_volunteer(
    db: Session, *, roles: Iterable[str], volunteer_id: uuid.UUID | str
) -> Volunteer:
    require_permission(roles, "volunteer:view")
    return _get_volunteer_or_404(db, volunteer_id)


# ---------------------------------------------------------------------------
# Volunteer task service
# ---------------------------------------------------------------------------


def _get_task_or_404(db: Session, task_id: uuid.UUID | str) -> VolunteerTask:
    obj = volunteer_tasks.get(db, _as_uuid(task_id))
    if obj is None:
        raise NotFoundError("Task not found", details={"id": str(task_id)})
    return obj


def _validate_due(due_at: datetime | None) -> None:
    if due_at is None:
        return
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    if due_at < datetime.now(timezone.utc):
        raise ValidationError("dueAt must be in the future")


def _ensure_active_volunteer(volunteer: Volunteer) -> None:
    if volunteer.status == VOLUNTEER_STATUS_INACTIVE:
        raise ConflictError(
            "Cannot assign a task to an inactive volunteer",
            details={"volunteerId": str(volunteer.id)},
        )


def create_task(
    db: Session,
    *,
    roles: Iterable[str],
    created_by: uuid.UUID | None,
    payload: dict[str, Any],
) -> VolunteerTask:
    require_permission(roles, "task:assign")

    data = dict(payload)
    # DTO → column
    for src, dst in (
        ("volunteerId", "volunteer_id"),
        ("campaignId", "campaign_id"),
        ("dueAt", "due_at"),
    ):
        if src in data:
            data[dst] = data.pop(src)

    volunteer_id = data.get("volunteer_id")
    if not volunteer_id:
        raise ValidationError("volunteerId is required")

    data["volunteer_id"] = _as_uuid(volunteer_id)
    if "campaign_id" in data:
        data["campaign_id"] = _as_uuid(data["campaign_id"])
    volunteer = _get_volunteer_or_404(db, data["volunteer_id"])
    _ensure_active_volunteer(volunteer)

    priority = data.get("priority") or TASK_PRIORITY_MEDIUM
    if priority not in TASK_PRIORITIES:
        raise ValidationError(f"Invalid task priority: {priority}")
    data["priority"] = priority

    _validate_due(data.get("due_at"))

    data["status"] = TASK_STATUS_PENDING
    data["assigned_at"] = datetime.now(timezone.utc)
    data["created_by_user_id"] = created_by
    task = volunteer_tasks.create(db, data)
    events.task_assigned(db, task)
    return task


def update_task(
    db: Session,
    *,
    roles: Iterable[str],
    task_id: uuid.UUID | str,
    payload: dict[str, Any],
) -> VolunteerTask:
    require_permission(roles, "task:manage")
    task = _get_task_or_404(db, task_id)
    if task.status in TASK_STATUSES_TERMINAL:
        raise ConflictError(
            "Cannot edit a task in a terminal state",
            details={"status": task.status},
        )
    data = dict(payload)
    for src, dst in (("campaignId", "campaign_id"), ("dueAt", "due_at")):
        if src in data:
            data[dst] = data.pop(src)
    if "campaign_id" in data:
        data["campaign_id"] = _as_uuid(data["campaign_id"])
    if "priority" in data and data["priority"] is not None:
        if data["priority"] not in TASK_PRIORITIES:
            raise ValidationError(f"Invalid task priority: {data['priority']}")
    _validate_due(data.get("due_at"))
    return volunteer_tasks.update(db, task, data)


def reassign_task(
    db: Session,
    *,
    roles: Iterable[str],
    task_id: uuid.UUID | str,
    volunteer_id: uuid.UUID | str,
) -> VolunteerTask:
    require_permission(roles, "task:assign")
    task = _get_task_or_404(db, task_id)
    if task.status not in (TASK_STATUS_PENDING, TASK_STATUS_ACCEPTED):
        raise ConflictError(
            "Only pending or accepted tasks can be reassigned",
            details={"status": task.status},
        )
    new_volunteer = _get_volunteer_or_404(db, volunteer_id)
    _ensure_active_volunteer(new_volunteer)
    previous_volunteer_id = task.volunteer_id
    updated = volunteer_tasks.update(
        db,
        task,
        {
            "volunteer_id": new_volunteer.id,
            "status": TASK_STATUS_PENDING,
            "assigned_at": datetime.now(timezone.utc),
        },
    )
    events.task_reassigned(db, updated, previous_volunteer_id)
    return updated


def change_status(
    db: Session,
    *,
    roles: Iterable[str],
    actor_user_id: uuid.UUID | None,
    task_id: uuid.UUID | str,
    new_status: str,
) -> VolunteerTask:
    """Apply the state-machine.

    Managers (``task:manage``) may perform any transition in
    :data:`TASK_TRANSITIONS_MANAGER`; assignees (``task:act``) are limited to
    :data:`TASK_TRANSITIONS_ACTOR` on tasks they own.
    """
    if new_status not in TASK_STATUSES:
        raise ValidationError(f"Invalid task status: {new_status}")

    task = _get_task_or_404(db, task_id)
    if task.status == new_status:
        return task

    # Prefer manager path when the caller has it.
    from app.security.rbac import has_permission

    is_manager = has_permission(roles, "task:manage")
    is_actor = has_permission(roles, "task:act")

    if not (is_manager or is_actor):
        raise ForbiddenError(
            "Missing permission: task:manage or task:act",
            details={"required": "task:manage|task:act"},
        )

    transitions = TASK_TRANSITIONS_MANAGER if is_manager else TASK_TRANSITIONS_ACTOR
    allowed = transitions.get(task.status, ())
    if new_status not in allowed:
        raise ConflictError(
            f"Illegal task transition {task.status} → {new_status}",
            details={"from": task.status, "to": new_status, "allowed": list(allowed)},
        )

    if not is_manager:
        # Assignees can only act on their own task.
        if actor_user_id is None:
            raise ForbiddenError("Assignee identity required to act on task")
        if task.volunteer is None or task.volunteer.user_id != actor_user_id:
            raise ForbiddenError("You can only act on tasks assigned to you")

    updates: dict[str, Any] = {"status": new_status}
    if new_status == TASK_STATUS_COMPLETED:
        updates["completed_at"] = datetime.now(timezone.utc)
    updated = volunteer_tasks.update(db, task, updates)
    if new_status == TASK_STATUS_COMPLETED:
        events.task_completed(db, updated)
    elif new_status == TASK_STATUS_CANCELLED:
        events.task_cancelled(db, updated)
    return updated


def complete_task(
    db: Session,
    *,
    roles: Iterable[str],
    actor_user_id: uuid.UUID | None,
    task_id: uuid.UUID | str,
) -> VolunteerTask:
    return change_status(
        db,
        roles=roles,
        actor_user_id=actor_user_id,
        task_id=task_id,
        new_status=TASK_STATUS_COMPLETED,
    )


def cancel_task(
    db: Session, *, roles: Iterable[str], task_id: uuid.UUID | str
) -> VolunteerTask:
    require_permission(roles, "task:manage")
    task = _get_task_or_404(db, task_id)
    if task.status in TASK_STATUSES_TERMINAL:
        raise ConflictError(
            "Task is already in a terminal state", details={"status": task.status}
        )
    updated = volunteer_tasks.update(db, task, {"status": TASK_STATUS_CANCELLED})
    events.task_cancelled(db, updated)
    return updated


def list_tasks(
    db: Session,
    *,
    roles: Iterable[str],
    filters: dict[str, Any],
) -> tuple[list[VolunteerTask], int]:
    require_permission(roles, "task:view")
    return volunteer_tasks.search(db, **filters)


def list_my_tasks(
    db: Session,
    *,
    roles: Iterable[str],
    user_id: uuid.UUID,
) -> list[VolunteerTask]:
    require_permission(roles, "task:view")
    require_permission(roles, "task:act")
    volunteer = volunteers.get_by_user(db, user_id)
    if volunteer is None:
        return []
    return volunteer_tasks.list_by_volunteer(db, volunteer.id)


__all__ = [
    # volunteer
    "create_volunteer",
    "update_volunteer",
    "set_status",
    "activate",
    "deactivate",
    "assign_organization",
    "list_volunteers",
    "get_volunteer",
    # tasks
    "create_task",
    "update_task",
    "reassign_task",
    "change_status",
    "complete_task",
    "cancel_task",
    "list_tasks",
    "list_my_tasks",
]
