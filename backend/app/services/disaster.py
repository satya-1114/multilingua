"""Disaster / Assignment / Attachment business services.

Pure business layer: input validation, state-machine enforcement, and
permission checks. Routers translate DTOs, call these functions, and
serialize the result. No FastAPI / HTTP concerns live here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.constants.disaster import (
    ASSIGNMENT_STATUS_ASSIGNED,
    ASSIGNMENT_STATUS_CANCELLED,
    ASSIGNMENT_STATUS_COMPLETED,
    ASSIGNMENT_STATUS_IN_PROGRESS,
    ASSIGNMENT_STATUSES,
    ASSIGNMENT_STATUSES_TERMINAL,
    ASSIGNMENT_TRANSITIONS,
    ATTACHMENT_KINDS,
    DISASTER_SEVERITIES,
    DISASTER_SEVERITY_MEDIUM,
    DISASTER_STATUS_ACTIVE,
    DISASTER_STATUS_CLOSED,
    DISASTER_STATUS_CONTAINED,
    DISASTER_STATUS_REPORTED,
    DISASTER_STATUS_RESOLVED,
    DISASTER_STATUS_VERIFIED,
    DISASTER_STATUSES,
    DISASTER_STATUSES_TERMINAL,
    DISASTER_TRANSITIONS,
    DISASTER_TYPES,
)
from app.constants.volunteer import VOLUNTEER_STATUS_INACTIVE
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.models.disaster import Disaster, DisasterAssignment, DisasterAttachment
from app.models.volunteer import Volunteer
from app.repositories.disaster import (
    disaster_assignments,
    disaster_attachments,
    disasters,
)
from app.repositories.volunteer import volunteers as volunteer_repo
from app.security.rbac import has_permission, require_permission
from app.services import disaster_events as events


# ---------------------------------------------------------------------------
# Helpers
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


def _get_disaster_or_404(db: Session, disaster_id: uuid.UUID | str) -> Disaster:
    obj = disasters.get(db, _as_uuid(disaster_id))
    if obj is None:
        raise NotFoundError("Disaster not found", details={"id": str(disaster_id)})
    return obj


def _get_assignment_or_404(
    db: Session, assignment_id: uuid.UUID | str
) -> DisasterAssignment:
    obj = disaster_assignments.get(db, _as_uuid(assignment_id))
    if obj is None:
        raise NotFoundError(
            "Assignment not found", details={"id": str(assignment_id)}
        )
    return obj


def _get_volunteer_or_404(db: Session, volunteer_id: uuid.UUID | str) -> Volunteer:
    obj = volunteer_repo.get(db, _as_uuid(volunteer_id))
    if obj is None:
        raise NotFoundError("Volunteer not found", details={"id": str(volunteer_id)})
    return obj


_ALIAS_MAP = {
    "disasterType": "disaster_type",
    "postalCode": "postal_code",
    "startedAt": "started_at",
    "resolvedAt": "resolved_at",
    "organizationId": "organization_id",
    "metadata": "metadata_",
}


def _normalize_disaster_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    for src, dst in _ALIAS_MAP.items():
        if src in data:
            data[dst] = data.pop(src)
    return data


# ---------------------------------------------------------------------------
# Disaster service
# ---------------------------------------------------------------------------


def create_disaster(
    db: Session,
    *,
    roles: Iterable[str],
    created_by: uuid.UUID | None,
    payload: dict[str, Any],
) -> Disaster:
    require_permission(roles, "disaster:create")
    data = _normalize_disaster_payload(payload)

    if not data.get("title"):
        raise ValidationError("title is required")
    dtype = data.get("disaster_type")
    if not dtype:
        raise ValidationError("disasterType is required")
    if dtype not in DISASTER_TYPES:
        raise ValidationError(f"Invalid disaster type: {dtype}")

    severity = data.get("severity") or DISASTER_SEVERITY_MEDIUM
    if severity not in DISASTER_SEVERITIES:
        raise ValidationError(f"Invalid severity: {severity}")
    data["severity"] = severity

    status = data.get("status") or DISASTER_STATUS_REPORTED
    if status not in DISASTER_STATUSES:
        raise ValidationError(f"Invalid disaster status: {status}")
    data["status"] = status

    if data.get("organization_id") is not None:
        data["organization_id"] = _as_uuid(data["organization_id"])

    data["created_by_user_id"] = created_by
    data.setdefault("metadata_", {})
    disaster = disasters.create(db, data)
    events.disaster_reported(db, disaster)
    return disaster


def update_disaster(
    db: Session,
    *,
    roles: Iterable[str],
    disaster_id: uuid.UUID | str,
    payload: dict[str, Any],
) -> Disaster:
    require_permission(roles, "disaster:update")
    disaster = _get_disaster_or_404(db, disaster_id)
    if disaster.status in DISASTER_STATUSES_TERMINAL:
        raise ConflictError(
            "Cannot edit a disaster in a terminal state",
            details={"status": disaster.status},
        )
    data = _normalize_disaster_payload(payload)
    if "disaster_type" in data and data["disaster_type"] is not None:
        if data["disaster_type"] not in DISASTER_TYPES:
            raise ValidationError(f"Invalid disaster type: {data['disaster_type']}")
    if "severity" in data and data["severity"] is not None:
        if data["severity"] not in DISASTER_SEVERITIES:
            raise ValidationError(f"Invalid severity: {data['severity']}")
    if "organization_id" in data and data["organization_id"] is not None:
        data["organization_id"] = _as_uuid(data["organization_id"])
    # Status changes go through the dedicated state-machine helper.
    data.pop("status", None)
    return disasters.update(db, disaster, data)


def _transition_status(
    db: Session,
    *,
    roles: Iterable[str],
    disaster_id: uuid.UUID | str,
    new_status: str,
    resolved_at: datetime | None = None,
) -> Disaster:
    require_permission(roles, "disaster:manage")
    if new_status not in DISASTER_STATUSES:
        raise ValidationError(f"Invalid disaster status: {new_status}")
    disaster = _get_disaster_or_404(db, disaster_id)
    if disaster.status == new_status:
        return disaster
    allowed = DISASTER_TRANSITIONS.get(disaster.status, ())
    if new_status not in allowed:
        raise ConflictError(
            f"Illegal disaster transition {disaster.status} → {new_status}",
            details={
                "from": disaster.status,
                "to": new_status,
                "allowed": list(allowed),
            },
        )
    updates: dict[str, Any] = {"status": new_status}
    is_reopen = (
        new_status == DISASTER_STATUS_ACTIVE
        and disaster.status == DISASTER_STATUS_RESOLVED
    )
    if new_status == DISASTER_STATUS_ACTIVE and disaster.started_at is None:
        updates["started_at"] = datetime.now(timezone.utc)
    if new_status == DISASTER_STATUS_RESOLVED:
        updates["resolved_at"] = resolved_at or datetime.now(timezone.utc)
    if is_reopen:
        # reopen: clear resolved_at
        updates["resolved_at"] = None
        # SQLAlchemy CRUDBase.update skips None values, so assign directly.
        disaster.resolved_at = None
    updated = disasters.update(db, disaster, updates)

    if is_reopen:
        events.disaster_reopened(db, updated)
    elif new_status == DISASTER_STATUS_VERIFIED:
        events.disaster_verified(db, updated)
    elif new_status == DISASTER_STATUS_ACTIVE:
        events.disaster_activated(db, updated)
    elif new_status == DISASTER_STATUS_CONTAINED:
        events.disaster_contained(db, updated)
    elif new_status == DISASTER_STATUS_RESOLVED:
        events.disaster_resolved(db, updated)
    elif new_status == DISASTER_STATUS_CLOSED:
        events.disaster_closed(db, updated)
    return updated




def verify_disaster(
    db: Session, *, roles: Iterable[str], disaster_id: uuid.UUID | str
) -> Disaster:
    return _transition_status(
        db, roles=roles, disaster_id=disaster_id, new_status=DISASTER_STATUS_VERIFIED
    )


def activate_disaster(
    db: Session, *, roles: Iterable[str], disaster_id: uuid.UUID | str
) -> Disaster:
    return _transition_status(
        db, roles=roles, disaster_id=disaster_id, new_status=DISASTER_STATUS_ACTIVE
    )


def contain_disaster(
    db: Session, *, roles: Iterable[str], disaster_id: uuid.UUID | str
) -> Disaster:
    return _transition_status(
        db, roles=roles, disaster_id=disaster_id, new_status=DISASTER_STATUS_CONTAINED
    )


def resolve_disaster(
    db: Session,
    *,
    roles: Iterable[str],
    disaster_id: uuid.UUID | str,
    resolved_at: datetime | None = None,
) -> Disaster:
    return _transition_status(
        db,
        roles=roles,
        disaster_id=disaster_id,
        new_status=DISASTER_STATUS_RESOLVED,
        resolved_at=resolved_at,
    )


def close_disaster(
    db: Session, *, roles: Iterable[str], disaster_id: uuid.UUID | str
) -> Disaster:
    return _transition_status(
        db, roles=roles, disaster_id=disaster_id, new_status=DISASTER_STATUS_CLOSED
    )


def reopen_disaster(
    db: Session, *, roles: Iterable[str], disaster_id: uuid.UUID | str
) -> Disaster:
    """Only RESOLVED disasters can be reopened (back to ACTIVE)."""
    return _transition_status(
        db, roles=roles, disaster_id=disaster_id, new_status=DISASTER_STATUS_ACTIVE
    )


def get_disaster(
    db: Session, *, roles: Iterable[str], disaster_id: uuid.UUID | str
) -> Disaster:
    require_permission(roles, "disaster:view")
    return _get_disaster_or_404(db, disaster_id)


def list_disasters(
    db: Session, *, roles: Iterable[str], filters: dict[str, Any]
) -> tuple[list[Disaster], int]:
    require_permission(roles, "disaster:view")
    return disasters.search(db, **filters)


# ---------------------------------------------------------------------------
# Assignment service
# ---------------------------------------------------------------------------


def _ensure_disaster_open(disaster: Disaster) -> None:
    if disaster.status in DISASTER_STATUSES_TERMINAL:
        raise ConflictError(
            "Cannot manage assignments on a resolved/closed disaster",
            details={"status": disaster.status},
        )


def _ensure_active_volunteer(volunteer: Volunteer) -> None:
    if volunteer.status == VOLUNTEER_STATUS_INACTIVE:
        raise ConflictError(
            "Cannot assign an inactive volunteer",
            details={"volunteerId": str(volunteer.id)},
        )


def _ensure_org_match(disaster: Disaster, volunteer: Volunteer) -> None:
    if (
        disaster.organization_id is not None
        and volunteer.organization_id is not None
        and disaster.organization_id != volunteer.organization_id
    ):
        raise ConflictError(
            "Volunteer belongs to a different organization",
            details={
                "disasterOrg": str(disaster.organization_id),
                "volunteerOrg": str(volunteer.organization_id),
            },
        )


def assign_volunteer(
    db: Session,
    *,
    roles: Iterable[str],
    assigned_by: uuid.UUID | None,
    disaster_id: uuid.UUID | str,
    payload: dict[str, Any],
) -> DisasterAssignment:
    require_permission(roles, "assignment:manage")
    disaster = _get_disaster_or_404(db, disaster_id)
    _ensure_disaster_open(disaster)

    data = dict(payload)
    volunteer_id = data.get("volunteerId") or data.get("volunteer_id")
    if not volunteer_id:
        raise ValidationError("volunteerId is required")
    volunteer = _get_volunteer_or_404(db, volunteer_id)
    _ensure_active_volunteer(volunteer)
    _ensure_org_match(disaster, volunteer)

    existing = disaster_assignments.get_assignment(
        db, disaster_id=disaster.id, volunteer_id=volunteer.id
    )
    if existing is not None and existing.status not in ASSIGNMENT_STATUSES_TERMINAL:
        raise ConflictError(
            "Volunteer is already assigned to this disaster",
            details={"assignmentId": str(existing.id)},
        )

    assignment = disaster_assignments.create(
        db,
        {
            "disaster_id": disaster.id,
            "volunteer_id": volunteer.id,
            "assigned_by_user_id": assigned_by,
            "role": data.get("role"),
            "notes": data.get("notes"),
            "status": ASSIGNMENT_STATUS_ASSIGNED,
            "assigned_at": datetime.now(timezone.utc),
        },
    )
    events.volunteer_assigned(db, assignment)
    return assignment


def reassign_volunteer(
    db: Session,
    *,
    roles: Iterable[str],
    assigned_by: uuid.UUID | None,
    assignment_id: uuid.UUID | str,
    volunteer_id: uuid.UUID | str,
) -> DisasterAssignment:
    require_permission(roles, "assignment:manage")
    assignment = _get_assignment_or_404(db, assignment_id)
    if assignment.status in ASSIGNMENT_STATUSES_TERMINAL:
        raise ConflictError(
            "Cannot reassign a terminal assignment",
            details={"status": assignment.status},
        )
    disaster = _get_disaster_or_404(db, assignment.disaster_id)
    _ensure_disaster_open(disaster)
    volunteer = _get_volunteer_or_404(db, volunteer_id)
    _ensure_active_volunteer(volunteer)
    _ensure_org_match(disaster, volunteer)

    duplicate = disaster_assignments.get_assignment(
        db, disaster_id=disaster.id, volunteer_id=volunteer.id
    )
    if (
        duplicate is not None
        and duplicate.id != assignment.id
        and duplicate.status not in ASSIGNMENT_STATUSES_TERMINAL
    ):
        raise ConflictError(
            "Target volunteer already has an active assignment on this disaster",
            details={"assignmentId": str(duplicate.id)},
        )

    previous_volunteer = assignment.volunteer
    previous_user_id = getattr(previous_volunteer, "user_id", None) if previous_volunteer else None
    updated = disaster_assignments.update(
        db,
        assignment,
        {
            "volunteer_id": volunteer.id,
            "assigned_by_user_id": assigned_by,
            "status": ASSIGNMENT_STATUS_ASSIGNED,
            "assigned_at": datetime.now(timezone.utc),
        },
    )
    events.volunteer_reassigned(db, updated, previous_user_id)
    return updated


def update_assignment(
    db: Session,
    *,
    roles: Iterable[str],
    assignment_id: uuid.UUID | str,
    payload: dict[str, Any],
) -> DisasterAssignment:
    require_permission(roles, "assignment:manage")
    assignment = _get_assignment_or_404(db, assignment_id)
    if assignment.status in ASSIGNMENT_STATUSES_TERMINAL:
        raise ConflictError(
            "Cannot edit a terminal assignment",
            details={"status": assignment.status},
        )
    data = {k: v for k, v in payload.items() if k in ("role", "notes")}
    return disaster_assignments.update(db, assignment, data)


def change_assignment_status(
    db: Session,
    *,
    roles: Iterable[str],
    actor_user_id: uuid.UUID | None,
    assignment_id: uuid.UUID | str,
    new_status: str,
    notes: str | None = None,
) -> DisasterAssignment:
    """Apply the assignment state machine.

    Managers (``assignment:manage``) can drive any allowed transition; the
    volunteer assignee (``assignment:act``) can drive transitions on their
    own assignment.
    """
    if new_status not in ASSIGNMENT_STATUSES:
        raise ValidationError(f"Invalid assignment status: {new_status}")

    assignment = _get_assignment_or_404(db, assignment_id)
    if assignment.status == new_status:
        return assignment

    is_manager = has_permission(roles, "assignment:manage")
    is_actor = has_permission(roles, "assignment:act")
    if not (is_manager or is_actor):
        raise ForbiddenError(
            "Missing permission: assignment:manage or assignment:act",
            details={"required": "assignment:manage|assignment:act"},
        )

    allowed = ASSIGNMENT_TRANSITIONS.get(assignment.status, ())
    if new_status not in allowed:
        raise ConflictError(
            f"Illegal assignment transition {assignment.status} → {new_status}",
            details={
                "from": assignment.status,
                "to": new_status,
                "allowed": list(allowed),
            },
        )

    if not is_manager:
        if actor_user_id is None:
            raise ForbiddenError("Assignee identity required to act on assignment")
        if assignment.volunteer is None or assignment.volunteer.user_id != actor_user_id:
            raise ForbiddenError("You can only act on your own assignments")

    updates: dict[str, Any] = {"status": new_status}
    if notes:
        updates["notes"] = notes
    if new_status == ASSIGNMENT_STATUS_COMPLETED:
        updates["completed_at"] = datetime.now(timezone.utc)
    updated = disaster_assignments.update(db, assignment, updates)
    if new_status == ASSIGNMENT_STATUS_COMPLETED:
        events.assignment_completed(db, updated)
    elif new_status == ASSIGNMENT_STATUS_CANCELLED:
        events.assignment_cancelled(db, updated)
    return updated


def complete_assignment(
    db: Session,
    *,
    roles: Iterable[str],
    actor_user_id: uuid.UUID | None,
    assignment_id: uuid.UUID | str,
    notes: str | None = None,
) -> DisasterAssignment:
    return change_assignment_status(
        db,
        roles=roles,
        actor_user_id=actor_user_id,
        assignment_id=assignment_id,
        new_status=ASSIGNMENT_STATUS_COMPLETED,
        notes=notes,
    )


def cancel_assignment(
    db: Session,
    *,
    roles: Iterable[str],
    assignment_id: uuid.UUID | str,
    notes: str | None = None,
) -> DisasterAssignment:
    require_permission(roles, "assignment:manage")
    assignment = _get_assignment_or_404(db, assignment_id)
    if assignment.status in ASSIGNMENT_STATUSES_TERMINAL:
        raise ConflictError(
            "Assignment is already in a terminal state",
            details={"status": assignment.status},
        )
    updates: dict[str, Any] = {"status": ASSIGNMENT_STATUS_CANCELLED}
    if notes:
        updates["notes"] = notes
    updated = disaster_assignments.update(db, assignment, updates)
    events.assignment_cancelled(db, updated)
    return updated


def list_assignments(
    db: Session,
    *,
    roles: Iterable[str],
    disaster_id: uuid.UUID | str | None = None,
    volunteer_id: uuid.UUID | str | None = None,
    statuses: Iterable[str] | None = None,
) -> list[DisasterAssignment]:
    require_permission(roles, "assignment:view")
    if disaster_id:
        return disaster_assignments.list_by_disaster(
            db, disaster_id, statuses=list(statuses) if statuses else None
        )
    if volunteer_id:
        return disaster_assignments.list_by_volunteer(
            db, volunteer_id, statuses=list(statuses) if statuses else None
        )
    return disaster_assignments.list_active(db)


# ---------------------------------------------------------------------------
# Attachment service (metadata only – upload lives elsewhere)
# ---------------------------------------------------------------------------


def register_attachment(
    db: Session,
    *,
    roles: Iterable[str],
    uploaded_by: uuid.UUID | None,
    disaster_id: uuid.UUID | str,
    payload: dict[str, Any],
) -> DisasterAttachment:
    require_permission(roles, "disaster:update")
    disaster = _get_disaster_or_404(db, disaster_id)

    data = dict(payload)
    # DTO → column
    for src, dst in (
        ("fileName", "file_name"),
        ("fileUrl", "file_url"),
        ("contentType", "content_type"),
        ("sizeBytes", "size_bytes"),
    ):
        if src in data:
            data[dst] = data.pop(src)

    kind = data.get("kind") or "image"
    if kind not in ATTACHMENT_KINDS:
        raise ValidationError(f"Invalid attachment kind: {kind}")
    if not data.get("file_name") or not data.get("file_url"):
        raise ValidationError("fileName and fileUrl are required")

    data["kind"] = kind
    data["disaster_id"] = disaster.id
    data["uploaded_by_user_id"] = uploaded_by
    return disaster_attachments.create(db, data)


def remove_attachment(
    db: Session, *, roles: Iterable[str], attachment_id: uuid.UUID | str
) -> None:
    require_permission(roles, "disaster:update")
    obj = disaster_attachments.get(db, _as_uuid(attachment_id))
    if obj is None:
        raise NotFoundError(
            "Attachment not found", details={"id": str(attachment_id)}
        )
    disaster_attachments.soft_delete(db, obj)


def list_attachments(
    db: Session,
    *,
    roles: Iterable[str],
    disaster_id: uuid.UUID | str,
    kind: str | None = None,
) -> list[DisasterAttachment]:
    require_permission(roles, "disaster:view")
    return disaster_attachments.list_by_disaster(db, disaster_id, kind=kind)


__all__ = [
    # disaster
    "create_disaster",
    "update_disaster",
    "verify_disaster",
    "activate_disaster",
    "contain_disaster",
    "resolve_disaster",
    "close_disaster",
    "reopen_disaster",
    "get_disaster",
    "list_disasters",
    # assignment
    "assign_volunteer",
    "reassign_volunteer",
    "update_assignment",
    "change_assignment_status",
    "complete_assignment",
    "cancel_assignment",
    "list_assignments",
    # attachment
    "register_attachment",
    "remove_attachment",
    "list_attachments",
]
