"""Disaster domain-event emitters.

Thin adapter that translates Disaster / DisasterAssignment business events
into the existing :mod:`app.services.notifications` pipeline. Kept isolated
from the core service so business logic remains pure and testable, and so
future channels (email, push, SMS) can be added here without touching the
service layer.

All emitters swallow errors: a notification failure MUST NOT abort the
underlying business operation. Errors are logged.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.disaster import Disaster, DisasterAssignment
from app.runtime.events import publish_event
from app.services import notifications as notif_service

log = get_logger(__name__)

CATEGORY = "disaster"


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
        log.warning("disaster notification emit failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


def _title(d: Disaster) -> str:
    return d.title or f"Disaster {d.id}"


def _href(d: Disaster) -> str:
    return f"/disasters/{d.id}"


# ---------------------------------------------------------------------------
# Disaster lifecycle
# ---------------------------------------------------------------------------


def _notify_reporter(db: Session, disaster: Disaster, *, title: str, message: str,
                     priority: str = "normal") -> None:
    _safe_create(
        db,
        user_id=disaster.created_by_user_id,
        title=title,
        message=message,
        priority=priority,
        href=_href(disaster),
    )


def disaster_reported(db: Session, disaster: Disaster) -> None:
    _notify_reporter(
        db, disaster,
        title=f"Disaster reported: {_title(disaster)}",
        message="Your disaster report has been recorded and is awaiting verification.",
    )
    publish_event(
        "disaster.reported",
        db=db,
        organization_id=getattr(disaster, "organization_id", None),
        actor_id=disaster.created_by_user_id,
        resource_type="disaster",
        resource_id=disaster.id,
        payload={
            "severity": getattr(disaster, "severity", None),
            "status": getattr(disaster, "status", None),
        },
    )


def disaster_verified(db: Session, disaster: Disaster) -> None:
    _notify_reporter(
        db, disaster,
        title=f"Disaster verified: {_title(disaster)}",
        message="This disaster has been verified.",
    )


def disaster_activated(db: Session, disaster: Disaster) -> None:
    _notify_reporter(
        db, disaster,
        title=f"Disaster active: {_title(disaster)}",
        message="Response has been activated for this disaster.",
        priority="high",
    )


def disaster_contained(db: Session, disaster: Disaster) -> None:
    _notify_reporter(
        db, disaster,
        title=f"Disaster contained: {_title(disaster)}",
        message="This disaster is now marked as contained.",
    )


def disaster_resolved(db: Session, disaster: Disaster) -> None:
    _notify_reporter(
        db, disaster,
        title=f"Disaster resolved: {_title(disaster)}",
        message="This disaster has been resolved.",
        priority="low",
    )
    publish_event(
        "disaster.resolved",
        db=db,
        organization_id=getattr(disaster, "organization_id", None),
        actor_id=disaster.created_by_user_id,
        resource_type="disaster",
        resource_id=disaster.id,
        payload={"status": getattr(disaster, "status", None)},
    )


def disaster_closed(db: Session, disaster: Disaster) -> None:
    _notify_reporter(
        db, disaster,
        title=f"Disaster closed: {_title(disaster)}",
        message="This disaster incident has been closed.",
        priority="low",
    )


def disaster_reopened(db: Session, disaster: Disaster) -> None:
    _notify_reporter(
        db, disaster,
        title=f"Disaster reopened: {_title(disaster)}",
        message="A previously resolved disaster has been reopened.",
        priority="high",
    )


# ---------------------------------------------------------------------------
# Assignment lifecycle
# ---------------------------------------------------------------------------


def _assignment_volunteer_user_id(assignment: DisasterAssignment) -> uuid.UUID | None:
    volunteer = getattr(assignment, "volunteer", None)
    return getattr(volunteer, "user_id", None) if volunteer else None


def volunteer_assigned(db: Session, assignment: DisasterAssignment) -> None:
    user_id = _assignment_volunteer_user_id(assignment)
    disaster = getattr(assignment, "disaster", None)
    label = _title(disaster) if disaster is not None else "a disaster"
    _safe_create(
        db,
        user_id=user_id,
        title=f"Assigned to disaster: {label}",
        message="You have been assigned to a disaster response.",
        priority="high",
        href=f"/disasters/{assignment.disaster_id}",
    )
    publish_event(
        "disaster.volunteer_assigned",
        db=db,
        actor_id=user_id,
        resource_type="disaster_assignment",
        resource_id=assignment.id,
        payload={
            "disasterId": str(assignment.disaster_id),
            "volunteerId": str(getattr(assignment, "volunteer_id", "")) or None,
        },
    )


def volunteer_reassigned(
    db: Session,
    assignment: DisasterAssignment,
    previous_volunteer_user_id: uuid.UUID | None,
) -> None:
    user_id = _assignment_volunteer_user_id(assignment)
    disaster = getattr(assignment, "disaster", None)
    label = _title(disaster) if disaster is not None else "a disaster"
    _safe_create(
        db,
        user_id=user_id,
        title=f"Reassigned to disaster: {label}",
        message="This disaster assignment has been moved to you.",
        priority="high",
        href=f"/disasters/{assignment.disaster_id}",
    )
    if previous_volunteer_user_id and previous_volunteer_user_id != user_id:
        _safe_create(
            db,
            user_id=previous_volunteer_user_id,
            title=f"Disaster reassignment: {label}",
            message="A disaster assignment previously held by you has been reassigned.",
            priority="normal",
            href=f"/disasters/{assignment.disaster_id}",
        )


def assignment_completed(db: Session, assignment: DisasterAssignment) -> None:
    user_id = _assignment_volunteer_user_id(assignment)
    disaster = getattr(assignment, "disaster", None)
    label = _title(disaster) if disaster is not None else "a disaster"
    _safe_create(
        db,
        user_id=user_id,
        title=f"Assignment completed: {label}",
        message="Thanks — your disaster assignment is marked as completed.",
        priority="low",
        href=f"/disasters/{assignment.disaster_id}",
    )


def assignment_cancelled(db: Session, assignment: DisasterAssignment) -> None:
    user_id = _assignment_volunteer_user_id(assignment)
    disaster = getattr(assignment, "disaster", None)
    label = _title(disaster) if disaster is not None else "a disaster"
    _safe_create(
        db,
        user_id=user_id,
        title=f"Assignment cancelled: {label}",
        message="Your disaster assignment has been cancelled.",
        priority="normal",
        href=f"/disasters/{assignment.disaster_id}",
    )


__all__ = [
    "CATEGORY",
    "disaster_reported",
    "disaster_verified",
    "disaster_activated",
    "disaster_contained",
    "disaster_resolved",
    "disaster_closed",
    "disaster_reopened",
    "volunteer_assigned",
    "volunteer_reassigned",
    "assignment_completed",
    "assignment_cancelled",
]
