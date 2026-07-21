"""Volunteer domain-event emitters.

Thin adapter that translates Volunteer / VolunteerTask business events into
the existing :mod:`app.services.notifications` pipeline. Kept separate so the
core service stays pure and testable, and so future channels (email, push)
can be added here without touching business logic.

All emitters swallow errors: a notification failure MUST NOT abort the
underlying business operation. Errors are logged.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.volunteer import Volunteer, VolunteerTask
from app.services import notifications as notif_service

from app.runtime.events import publish_event

log = get_logger(__name__)

CATEGORY = "volunteer"


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
        log.warning("volunteer notification emit failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Volunteer lifecycle
# ---------------------------------------------------------------------------


def volunteer_activated(db: Session, volunteer: Volunteer) -> None:
    _safe_create(
        db,
        user_id=volunteer.user_id,
        title="You're active as a volunteer",
        message="Your volunteer profile is now available for task assignments.",
        priority="normal",
        href=f"/volunteers/{volunteer.id}",
    )
    publish_event(
        "volunteer.activated",
        db=db,
        organization_id=getattr(volunteer, "organization_id", None),
        actor_id=volunteer.user_id,
        resource_type="volunteer",
        resource_id=volunteer.id,
        payload={"status": getattr(volunteer, "status", None)},
    )


def volunteer_deactivated(db: Session, volunteer: Volunteer) -> None:
    _safe_create(
        db,
        user_id=volunteer.user_id,
        title="Volunteer profile deactivated",
        message="Your volunteer profile has been set to inactive.",
        priority="normal",
        href=f"/volunteers/{volunteer.id}",
    )


# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------


def task_assigned(db: Session, task: VolunteerTask) -> None:
    volunteer = task.volunteer
    if volunteer is None:
        return
    _safe_create(
        db,
        user_id=volunteer.user_id,
        title=f"New task: {task.title}",
        message=task.description or "You have been assigned a new task.",
        priority=task.priority or "normal",
        href=f"/tasks/{task.id}",
    )
    publish_event(
        "volunteer.task.assigned",
        db=db,
        actor_id=volunteer.user_id,
        resource_type="volunteer_task",
        resource_id=task.id,
        payload={
            "volunteerId": str(volunteer.id),
            "priority": task.priority,
            "title": task.title,
        },
    )


def task_reassigned(db: Session, task: VolunteerTask, previous_volunteer_id: uuid.UUID | None) -> None:
    volunteer = task.volunteer
    if volunteer is not None:
        _safe_create(
            db,
            user_id=volunteer.user_id,
            title=f"Task reassigned to you: {task.title}",
            message="A task has been reassigned to you and is pending your acceptance.",
            priority=task.priority or "normal",
            href=f"/tasks/{task.id}",
        )
    # Notify the previous assignee too (if any and different).
    if previous_volunteer_id and (volunteer is None or previous_volunteer_id != volunteer.id):
        from app.repositories.volunteer import volunteers as vol_repo

        prev = vol_repo.get(db, previous_volunteer_id)
        if prev is not None:
            _safe_create(
                db,
                user_id=prev.user_id,
                title=f"Task reassigned: {task.title}",
                message="A task previously assigned to you has been reassigned.",
                priority="low",
                href=f"/tasks/{task.id}",
            )


def task_completed(db: Session, task: VolunteerTask) -> None:
    volunteer = task.volunteer
    if volunteer is None:
        return
    _safe_create(
        db,
        user_id=volunteer.user_id,
        title=f"Task completed: {task.title}",
        message="Thanks — this task is marked as completed.",
        priority="low",
        href=f"/tasks/{task.id}",
    )
    publish_event(
        "volunteer.task.completed",
        db=db,
        actor_id=volunteer.user_id,
        resource_type="volunteer_task",
        resource_id=task.id,
        payload={"volunteerId": str(volunteer.id), "title": task.title},
    )
    # Also notify the creator (usually a campaign manager), if different.
    if task.created_by_user_id and task.created_by_user_id != volunteer.user_id:
        _safe_create(
            db,
            user_id=task.created_by_user_id,
            title=f"Task completed: {task.title}",
            message="A task you created has been marked as completed.",
            priority="low",
            href=f"/tasks/{task.id}",
        )


def task_cancelled(db: Session, task: VolunteerTask) -> None:
    volunteer = task.volunteer
    if volunteer is None:
        return
    _safe_create(
        db,
        user_id=volunteer.user_id,
        title=f"Task cancelled: {task.title}",
        message="This task has been cancelled by a manager.",
        priority="normal",
        href=f"/tasks/{task.id}",
    )


__all__ = [
    "CATEGORY",
    "volunteer_activated",
    "volunteer_deactivated",
    "task_assigned",
    "task_reassigned",
    "task_completed",
    "task_cancelled",
]
