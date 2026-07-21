"""Volunteer-task HTTP routes.

Thin FastAPI layer over :mod:`app.services.volunteer` for task operations.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import current_user, require_perm
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.volunteer import (
    TaskPriority,
    TaskStatus,
    VolunteerTaskCreate,
    VolunteerTaskStatusUpdate,
    VolunteerTaskUpdate,
)
from app.services import audit, volunteer as svc

from .volunteers import _roles, _serialize_task

router = APIRouter()


# ---------------------------------------------------------------------------
# List / My
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="List tasks",
    description="Search & paginate volunteer tasks. Requires `task:view`.",
    response_model=None,
)
def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200, alias="pageSize"),
    volunteer_id: uuid.UUID | None = Query(None, alias="volunteerId"),
    campaign_id: uuid.UUID | None = Query(None, alias="campaignId"),
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    search: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("task:view")),
):
    filters = {
        "page": page,
        "page_size": page_size,
        "volunteer_id": volunteer_id,
        "campaign_id": campaign_id,
        "status": status,
        "priority": priority,
        "search": search,
    }
    items, total = svc.list_tasks(db, roles=_roles(user), filters=filters)
    return paginated([_serialize_task(t) for t in items], page, page_size, total)


@router.get(
    "/mine",
    summary="List my tasks",
    description=(
        "Return the tasks assigned to the authenticated volunteer. "
        "Requires `task:view` and `task:act`."
    ),
    response_model=None,
)
def list_my_tasks(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    items = svc.list_my_tasks(db, roles=_roles(user), user_id=user.id)
    return ok([_serialize_task(t) for t in items])


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=201,
    summary="Create a task",
    description="Assign a new task to a volunteer. Requires `task:assign`.",
    response_model=None,
)
def create_task(
    payload: VolunteerTaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.create_task(
        db,
        roles=_roles(user),
        created_by=user.id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="create", module="task", actor_id=user.id,
              entity_id=str(t.id), entity_label=t.title,
              metadata={"volunteerId": str(t.volunteer_id)})
    return ok(_serialize_task(t))


@router.patch(
    "/{task_id}",
    summary="Edit a task",
    description="Edit assignment fields (title, description, priority, dueAt, campaignId). Requires `task:manage`.",
    response_model=None,
)
def update_task(
    task_id: uuid.UUID,
    payload: VolunteerTaskUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.update_task(
        db,
        roles=_roles(user),
        task_id=task_id,
        payload=payload.model_dump(exclude_none=True),
    )
    return ok(_serialize_task(t))


@router.post(
    "/{task_id}/assign",
    summary="Reassign a task",
    description="Reassign a pending / accepted task to another volunteer. Requires `task:assign`.",
    response_model=None,
)
def reassign_task(
    task_id: uuid.UUID,
    payload: dict[str, Any] = Body(..., examples=[{"volunteerId": "..."}]),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    volunteer_id = payload.get("volunteerId")
    if not volunteer_id:
        from app.core.exceptions import ValidationError

        raise ValidationError("volunteerId is required")
    t = svc.reassign_task(
        db, roles=_roles(user), task_id=task_id, volunteer_id=volunteer_id
    )
    audit.log(db, action="reassign", module="task", actor_id=user.id,
              entity_id=str(t.id), metadata={"volunteerId": str(t.volunteer_id)})
    return ok(_serialize_task(t))


@router.patch(
    "/{task_id}/status",
    summary="Change a task's status",
    description=(
        "Transition a task through the state machine. "
        "Volunteers act on their own tasks (`task:act`); campaign managers can "
        "force any transition (`task:manage`)."
    ),
    response_model=None,
)
def change_task_status(
    task_id: uuid.UUID,
    payload: VolunteerTaskStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.change_status(
        db,
        roles=_roles(user),
        actor_user_id=user.id,
        task_id=task_id,
        new_status=payload.status,
    )
    return ok(_serialize_task(t))


@router.post(
    "/{task_id}/complete",
    summary="Complete a task",
    description="Mark an in-progress task as completed. Requires `task:act` (assignee) or `task:manage`.",
    response_model=None,
)
def complete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.complete_task(
        db, roles=_roles(user), actor_user_id=user.id, task_id=task_id
    )
    audit.log(db, action="complete", module="task", actor_id=user.id,
              entity_id=str(t.id), entity_label=t.title)
    return ok(_serialize_task(t))


@router.delete(
    "/{task_id}",
    summary="Cancel a task",
    description="Cancel (soft-terminate) a task. Requires `task:manage`.",
    response_model=None,
)
def cancel_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.cancel_task(db, roles=_roles(user), task_id=task_id)
    audit.log(db, action="cancel", module="task", actor_id=user.id,
              entity_id=str(t.id), entity_label=t.title)
    return ok(_serialize_task(t))
