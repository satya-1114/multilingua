"""Volunteer HTTP routes.

Thin FastAPI layer over :mod:`app.services.volunteer`. Routers validate DTOs,
inject the current user, call the service, and serialize the result via the
standard :func:`app.core.responses.ok` / :func:`paginated` envelopes.
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
from app.models.volunteer import Volunteer
from app.schemas.volunteer import (
    VolunteerCreate,
    VolunteerDto,
    VolunteerStatus,
    VolunteerTaskDto,
    VolunteerUpdate,
)
from app.services import audit, volunteer as svc
from app.repositories.volunteer import volunteer_tasks as tasks_repo

router = APIRouter()


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _iso(dt) -> str | None:
    return dt.isoformat() if dt is not None else None


def _serialize_volunteer(v: Volunteer) -> dict[str, Any]:
    contact = None
    if v.emergency_contact_name or v.emergency_contact_phone or v.emergency_contact_relation:
        contact = {
            "name": v.emergency_contact_name,
            "phone": v.emergency_contact_phone,
            "relation": v.emergency_contact_relation,
        }
    user = getattr(v, "user", None)
    tasks = list(getattr(v, "tasks", []) or [])
    active_count = sum(
        1 for t in tasks if t.status in ("pending", "accepted", "in_progress")
    )
    completed_count = sum(1 for t in tasks if t.status == "completed")
    campaign_ids = sorted({
        str(t.campaign_id) for t in tasks if t.campaign_id is not None
    })
    return {
        "id": str(v.id),
        "userId": str(v.user_id),
        "organizationId": str(v.organization_id) if v.organization_id else None,
        "fullName": getattr(user, "full_name", "") or "",
        "email": getattr(user, "email", "") or "",
        "phone": "",
        "avatarUrl": getattr(user, "avatar_url", None),
        "languages": list(v.languages or []),
        "skills": list(v.skills or []),
        "currentLocation": v.current_location,
        "availability": v.availability,
        "status": v.status,
        "emergencyContact": contact,
        "assignedCampaignIds": campaign_ids,
        "activeTaskCount": active_count,
        "completedTaskCount": completed_count,
        "createdAt": _iso(v.created_at),
        "updatedAt": _iso(v.updated_at),
    }


def _serialize_task(t) -> dict[str, Any]:
    volunteer = getattr(t, "volunteer", None)
    volunteer_user = getattr(volunteer, "user", None) if volunteer else None
    campaign = getattr(t, "campaign", None)
    return {
        "id": str(t.id),
        "volunteerId": str(t.volunteer_id),
        "volunteerName": getattr(volunteer_user, "full_name", None),
        "campaignId": str(t.campaign_id) if t.campaign_id else None,
        "campaignName": getattr(campaign, "name", None),
        "title": t.title,
        "description": t.description,
        "priority": t.priority,
        "status": t.status,
        "assignedAt": _iso(t.assigned_at) or _iso(t.created_at),
        "dueAt": _iso(t.due_at),
        "completedAt": _iso(t.completed_at),
        "createdByUserId": str(t.created_by_user_id) if t.created_by_user_id else None,
        "createdBy": str(t.created_by_user_id) if t.created_by_user_id else None,
        "createdAt": _iso(t.created_at),
        "updatedAt": _iso(t.updated_at),
    }


def _roles(user: User) -> list[str]:
    return [r.name for r in getattr(user, "roles", []) or []]


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="List volunteers",
    description="Search & paginate volunteer profiles. Requires `volunteer:view`.",
    response_model=None,
)
def list_volunteers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200, alias="pageSize"),
    search: str | None = Query(None, max_length=200),
    language: str | None = None,
    skill: str | None = None,
    location: str | None = None,
    availability: str | None = None,
    status: VolunteerStatus | None = None,
    organization_id: uuid.UUID | None = Query(None, alias="organizationId"),
    sort_by: str | None = Query(None, alias="sortBy", max_length=64),
    sort_dir: str = Query("desc", alias="sortDir", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("volunteer:view")),
):
    filters = {
        "page": page,
        "page_size": page_size,
        "search": search,
        "language": language,
        "skill": skill,
        "location": location,
        "availability": availability,
        "status": status,
        "organization_id": organization_id,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
    }
    items, total = svc.list_volunteers(db, roles=_roles(user), filters=filters)
    return paginated([_serialize_volunteer(v) for v in items], page, page_size, total)


@router.get(
    "/{volunteer_id}",
    summary="Get a volunteer",
    description="Fetch a single volunteer profile. Requires `volunteer:view`.",
    response_model=None,
)
def get_volunteer(
    volunteer_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    v = svc.get_volunteer(db, roles=_roles(user), volunteer_id=volunteer_id)
    return ok(_serialize_volunteer(v))


@router.get(
    "/{volunteer_id}/tasks",
    summary="List a volunteer's tasks",
    description="Return the tasks assigned to a volunteer. Requires `volunteer:view`.",
    response_model=None,
)
def list_volunteer_tasks(
    volunteer_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("volunteer:view")),
):
    # Ensure the volunteer exists (raises 404) before returning.
    svc.get_volunteer(db, roles=_roles(user), volunteer_id=volunteer_id)
    items = tasks_repo.list_by_volunteer(db, volunteer_id)
    return ok([_serialize_task(t) for t in items])


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------


@router.post(
    "",
    status_code=201,
    summary="Create a volunteer",
    description="Create a new volunteer profile. Requires `volunteer:manage`.",
    response_model=None,
)
def create_volunteer(
    payload: VolunteerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    v = svc.create_volunteer(
        db, roles=_roles(user), payload=payload.model_dump(exclude_none=True)
    )
    audit.log(db, action="create", module="volunteer", actor_id=user.id,
              entity_id=str(v.id), entity_label=str(v.user_id))
    return ok(_serialize_volunteer(v))


@router.patch(
    "/{volunteer_id}",
    summary="Update a volunteer",
    description="Update editable fields of a volunteer profile. Requires `volunteer:manage`.",
    response_model=None,
)
def update_volunteer(
    volunteer_id: uuid.UUID,
    payload: VolunteerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    v = svc.update_volunteer(
        db,
        roles=_roles(user),
        volunteer_id=volunteer_id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="update", module="volunteer", actor_id=user.id,
              entity_id=str(v.id), metadata=payload.model_dump(exclude_none=True))
    return ok(_serialize_volunteer(v))


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


@router.post(
    "/{volunteer_id}/activate",
    summary="Activate a volunteer",
    description="Mark the volunteer as `available`. Requires `volunteer:manage`.",
    response_model=None,
)
def activate_volunteer(
    volunteer_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    v = svc.activate(db, roles=_roles(user), volunteer_id=volunteer_id)
    return ok(_serialize_volunteer(v))


@router.post(
    "/{volunteer_id}/deactivate",
    summary="Deactivate a volunteer",
    description="Mark the volunteer as `inactive`. Requires `volunteer:manage`.",
    response_model=None,
)
def deactivate_volunteer(
    volunteer_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    v = svc.deactivate(db, roles=_roles(user), volunteer_id=volunteer_id)
    return ok(_serialize_volunteer(v))


@router.post(
    "/{volunteer_id}/organization",
    summary="Assign / clear a volunteer's organization",
    description="Set or unset the organization for a volunteer. Requires `volunteer:manage`.",
    response_model=None,
)
def assign_organization(
    volunteer_id: uuid.UUID,
    payload: dict[str, Any] = Body(..., examples=[{"organizationId": "..."}]),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    org_id = payload.get("organizationId")
    v = svc.assign_organization(
        db,
        roles=_roles(user),
        volunteer_id=volunteer_id,
        organization_id=org_id,
    )
    return ok(_serialize_volunteer(v))
