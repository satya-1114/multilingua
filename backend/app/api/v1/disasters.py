"""Disaster / Assignment / Attachment HTTP routes.

Thin FastAPI layer over :mod:`app.services.disaster`. Routers validate DTOs,
inject the current user, call the service, and serialize the result via the
standard :func:`app.core.responses.ok` / :func:`paginated` envelopes. All
business logic (state machines, permissions, validation) lives in the
service layer.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import current_user, require_perm
from app.dependencies.db import get_db
from app.models.disaster import Disaster, DisasterAssignment, DisasterAttachment
from app.models.user import User
from app.schemas.disaster import (
    AssignmentStatus,
    DisasterAssignmentCreate,
    DisasterAssignmentStatusUpdate,
    DisasterAssignmentUpdate,
    DisasterAttachmentCreate,
    DisasterCreate,
    DisasterSeverity,
    DisasterStatus,
    DisasterType,
    DisasterUpdate,
)
from app.services import audit, disaster as svc

router = APIRouter()


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _iso(dt) -> str | None:
    return dt.isoformat() if dt is not None else None


def _roles(user: User) -> list[str]:
    return [r.name for r in getattr(user, "roles", []) or []]


def _serialize_disaster(d: Disaster) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "title": d.title,
        "description": d.description,
        "disasterType": d.disaster_type,
        "severity": d.severity,
        "status": d.status,
        "latitude": d.latitude,
        "longitude": d.longitude,
        "address": d.address,
        "city": d.city,
        "district": d.district,
        "state": d.state,
        "country": d.country,
        "postalCode": d.postal_code,
        "startedAt": _iso(d.started_at),
        "resolvedAt": _iso(d.resolved_at),
        "organizationId": str(d.organization_id) if d.organization_id else None,
        "createdByUserId": str(d.created_by_user_id) if d.created_by_user_id else None,
        "metadata": dict(d.metadata_ or {}),
        "createdAt": _iso(d.created_at),
        "updatedAt": _iso(d.updated_at),
    }


def _serialize_assignment(a: DisasterAssignment) -> dict[str, Any]:
    volunteer = getattr(a, "volunteer", None)
    volunteer_user = getattr(volunteer, "user", None) if volunteer else None
    return {
        "id": str(a.id),
        "disasterId": str(a.disaster_id),
        "volunteerId": str(a.volunteer_id),
        "volunteerName": getattr(volunteer_user, "full_name", None),
        "assignedByUserId": str(a.assigned_by_user_id) if a.assigned_by_user_id else None,
        "role": a.role,
        "status": a.status,
        "notes": a.notes,
        "assignedAt": _iso(a.assigned_at),
        "completedAt": _iso(a.completed_at),
        "createdAt": _iso(a.created_at),
        "updatedAt": _iso(a.updated_at),
    }


def _serialize_attachment(x: DisasterAttachment) -> dict[str, Any]:
    return {
        "id": str(x.id),
        "disasterId": str(x.disaster_id),
        "uploadedByUserId": str(x.uploaded_by_user_id) if x.uploaded_by_user_id else None,
        "kind": x.kind,
        "fileName": x.file_name,
        "fileUrl": x.file_url,
        "contentType": x.content_type,
        "sizeBytes": x.size_bytes,
        "caption": x.caption,
        "createdAt": _iso(x.created_at),
    }


# ---------------------------------------------------------------------------
# Assignment routes  (literal-prefixed – registered BEFORE /{disaster_id}/*)
# ---------------------------------------------------------------------------


@router.patch(
    "/assignments/{assignment_id}",
    summary="Update assignment metadata",
    description="Edit role/notes on an assignment. Requires `assignment:manage`.",
    response_model=None,
)
def update_assignment(
    assignment_id: uuid.UUID,
    payload: DisasterAssignmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    a = svc.update_assignment(
        db,
        roles=_roles(user),
        assignment_id=assignment_id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="update", module="assignment", actor_id=user.id,
              entity_id=str(a.id), metadata=payload.model_dump(exclude_none=True))
    return ok(_serialize_assignment(a))


@router.post(
    "/assignments/{assignment_id}/reassign",
    summary="Reassign an assignment to a different volunteer",
    description="Move an active assignment to another volunteer. Requires `assignment:manage`.",
    response_model=None,
)
def reassign_assignment(
    assignment_id: uuid.UUID,
    payload: dict[str, Any] = Body(..., examples=[{"volunteerId": "..."}]),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    volunteer_id = payload.get("volunteerId") or payload.get("volunteer_id")
    a = svc.reassign_volunteer(
        db,
        roles=_roles(user),
        assigned_by=user.id,
        assignment_id=assignment_id,
        volunteer_id=volunteer_id,
    )
    audit.log(db, action="reassign", module="assignment", actor_id=user.id,
              entity_id=str(a.id),
              metadata={"volunteerId": str(volunteer_id) if volunteer_id else None})
    return ok(_serialize_assignment(a))


@router.patch(
    "/assignments/{assignment_id}/status",
    summary="Change assignment status",
    description=(
        "Drive the assignment state machine. Managers with `assignment:manage` can "
        "apply any allowed transition; assignees with `assignment:act` can drive "
        "transitions on their own assignment."
    ),
    response_model=None,
)
def change_assignment_status(
    assignment_id: uuid.UUID,
    payload: DisasterAssignmentStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    a = svc.change_assignment_status(
        db,
        roles=_roles(user),
        actor_user_id=user.id,
        assignment_id=assignment_id,
        new_status=payload.status,
        notes=payload.notes,
    )
    audit.log(db, action="status_change", module="assignment", actor_id=user.id,
              entity_id=str(a.id), metadata={"status": payload.status})
    return ok(_serialize_assignment(a))


@router.post(
    "/assignments/{assignment_id}/complete",
    summary="Complete an assignment",
    description="Mark the assignment as `completed`. Requires manage or act permission on own assignment.",
    response_model=None,
)
def complete_assignment(
    assignment_id: uuid.UUID,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    notes = (payload or {}).get("notes") if isinstance(payload, dict) else None
    a = svc.complete_assignment(
        db,
        roles=_roles(user),
        actor_user_id=user.id,
        assignment_id=assignment_id,
        notes=notes,
    )
    audit.log(db, action="complete", module="assignment", actor_id=user.id,
              entity_id=str(a.id))
    return ok(_serialize_assignment(a))


@router.delete(
    "/assignments/{assignment_id}",
    summary="Cancel an assignment",
    description="Cancel a non-terminal assignment. Requires `assignment:manage`.",
    response_model=None,
)
def cancel_assignment(
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    a = svc.cancel_assignment(
        db, roles=_roles(user), assignment_id=assignment_id
    )
    audit.log(db, action="cancel", module="assignment", actor_id=user.id,
              entity_id=str(a.id))
    return ok(_serialize_assignment(a))


# ---------------------------------------------------------------------------
# Attachment routes  (literal-prefixed – registered BEFORE /{disaster_id}/*)
# ---------------------------------------------------------------------------


@router.delete(
    "/attachments/{attachment_id}",
    summary="Remove a disaster attachment",
    description="Soft-delete an attachment (metadata only). Requires `disaster:update`.",
    response_model=None,
)
def delete_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    svc.remove_attachment(db, roles=_roles(user), attachment_id=attachment_id)
    audit.log(db, action="delete", module="attachment", actor_id=user.id,
              entity_id=str(attachment_id))
    return ok({"id": str(attachment_id), "deleted": True})


# ---------------------------------------------------------------------------
# Disaster list / get / create / update
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="List disasters",
    description="Search & paginate disaster incidents. Requires `disaster:view`.",
    response_model=None,
)
def list_disasters(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200, alias="pageSize"),
    search: str | None = Query(None, max_length=200),
    disaster_type: DisasterType | None = Query(None, alias="disasterType"),
    severity: DisasterSeverity | None = None,
    status: DisasterStatus | None = None,
    organization_id: uuid.UUID | None = Query(None, alias="organizationId"),
    city: str | None = None,
    district: str | None = None,
    state: str | None = None,
    country: str | None = None,
    volunteer_id: uuid.UUID | None = Query(None, alias="volunteerId"),
    sort_by: str | None = Query(None, alias="sortBy", max_length=64),
    sort_dir: str = Query("desc", alias="sortDir", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("disaster:view")),
):
    filters = {
        "page": page,
        "page_size": page_size,
        "search": search,
        "disaster_type": disaster_type,
        "severity": severity,
        "status": status,
        "organization_id": organization_id,
        "city": city,
        "district": district,
        "state": state,
        "country": country,
        "volunteer_id": volunteer_id,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
    }
    items, total = svc.list_disasters(db, roles=_roles(user), filters=filters)
    return paginated(
        [_serialize_disaster(d) for d in items], page, page_size, total
    )


@router.get(
    "/{disaster_id}",
    summary="Get a disaster",
    description="Fetch a single disaster incident. Requires `disaster:view`.",
    response_model=None,
)
def get_disaster(
    disaster_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    d = svc.get_disaster(db, roles=_roles(user), disaster_id=disaster_id)
    return ok(_serialize_disaster(d))


@router.post(
    "",
    status_code=201,
    summary="Create a disaster",
    description="Register a new disaster incident. Requires `disaster:create`.",
    response_model=None,
)
def create_disaster(
    payload: DisasterCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    d = svc.create_disaster(
        db,
        roles=_roles(user),
        created_by=user.id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="create", module="disaster", actor_id=user.id,
              entity_id=str(d.id), entity_label=d.title)
    return ok(_serialize_disaster(d))


@router.patch(
    "/{disaster_id}",
    summary="Update a disaster",
    description="Update editable fields of a disaster. Requires `disaster:update`.",
    response_model=None,
)
def update_disaster(
    disaster_id: uuid.UUID,
    payload: DisasterUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    d = svc.update_disaster(
        db,
        roles=_roles(user),
        disaster_id=disaster_id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="update", module="disaster", actor_id=user.id,
              entity_id=str(d.id), metadata=payload.model_dump(exclude_none=True))
    return ok(_serialize_disaster(d))


# ---------------------------------------------------------------------------
# Disaster state-machine transitions
# ---------------------------------------------------------------------------


def _transition_endpoint(action_name: str, service_fn, *, audit_action: str):
    def _handler(
        disaster_id: uuid.UUID,
        db: Session = Depends(get_db),
        user: User = Depends(current_user),
    ):
        d = service_fn(db, roles=_roles(user), disaster_id=disaster_id)
        audit.log(db, action=audit_action, module="disaster", actor_id=user.id,
                  entity_id=str(d.id), entity_label=d.title)
        return ok(_serialize_disaster(d))

    _handler.__name__ = action_name
    return _handler


router.add_api_route(
    "/{disaster_id}/verify",
    _transition_endpoint("verify_disaster", svc.verify_disaster, audit_action="verify"),
    methods=["POST"],
    summary="Verify a disaster",
    description="Transition a disaster to `verified`. Requires `disaster:manage`.",
    response_model=None,
)
router.add_api_route(
    "/{disaster_id}/activate",
    _transition_endpoint("activate_disaster", svc.activate_disaster, audit_action="activate"),
    methods=["POST"],
    summary="Activate a disaster",
    description="Transition a disaster to `active`. Requires `disaster:manage`.",
    response_model=None,
)
router.add_api_route(
    "/{disaster_id}/contain",
    _transition_endpoint("contain_disaster", svc.contain_disaster, audit_action="contain"),
    methods=["POST"],
    summary="Mark a disaster as contained",
    description="Transition a disaster to `contained`. Requires `disaster:manage`.",
    response_model=None,
)
router.add_api_route(
    "/{disaster_id}/close",
    _transition_endpoint("close_disaster", svc.close_disaster, audit_action="close"),
    methods=["POST"],
    summary="Close a disaster",
    description="Transition a disaster to `closed`. Requires `disaster:manage`.",
    response_model=None,
)
router.add_api_route(
    "/{disaster_id}/reopen",
    _transition_endpoint("reopen_disaster", svc.reopen_disaster, audit_action="reopen"),
    methods=["POST"],
    summary="Reopen a resolved disaster",
    description="Transition a resolved disaster back to `active`. Requires `disaster:manage`.",
    response_model=None,
)


@router.post(
    "/{disaster_id}/resolve",
    summary="Resolve a disaster",
    description="Transition a disaster to `resolved`. Requires `disaster:manage`.",
    response_model=None,
)
def resolve_disaster(
    disaster_id: uuid.UUID,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    resolved_at = None
    if isinstance(payload, dict):
        resolved_at = payload.get("resolvedAt") or payload.get("resolved_at")
    d = svc.resolve_disaster(
        db,
        roles=_roles(user),
        disaster_id=disaster_id,
        resolved_at=resolved_at,
    )
    audit.log(db, action="resolve", module="disaster", actor_id=user.id,
              entity_id=str(d.id), entity_label=d.title)
    return ok(_serialize_disaster(d))


# ---------------------------------------------------------------------------
# Disaster-scoped assignment routes
# ---------------------------------------------------------------------------


@router.get(
    "/{disaster_id}/assignments",
    summary="List assignments for a disaster",
    description="Return assignments attached to a disaster. Requires `assignment:view`.",
    response_model=None,
)
def list_disaster_assignments(
    disaster_id: uuid.UUID,
    status: AssignmentStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    # Ensure the disaster exists / caller may view it.
    svc.get_disaster(db, roles=_roles(user), disaster_id=disaster_id)
    items = svc.list_assignments(
        db,
        roles=_roles(user),
        disaster_id=disaster_id,
        statuses=[status] if status else None,
    )
    return ok([_serialize_assignment(a) for a in items])


@router.post(
    "/{disaster_id}/assignments",
    status_code=201,
    summary="Assign a volunteer to a disaster",
    description="Create a new assignment for a volunteer. Requires `assignment:manage`.",
    response_model=None,
)
def create_disaster_assignment(
    disaster_id: uuid.UUID,
    payload: DisasterAssignmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    a = svc.assign_volunteer(
        db,
        roles=_roles(user),
        assigned_by=user.id,
        disaster_id=disaster_id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="assign", module="assignment", actor_id=user.id,
              entity_id=str(a.id),
              metadata={"disasterId": str(disaster_id),
                        "volunteerId": str(a.volunteer_id)})
    return ok(_serialize_assignment(a))


# ---------------------------------------------------------------------------
# Disaster-scoped attachment routes  (metadata only)
# ---------------------------------------------------------------------------


@router.get(
    "/{disaster_id}/attachments",
    summary="List attachments for a disaster",
    description="Return attachment metadata. Requires `disaster:view`.",
    response_model=None,
)
def list_disaster_attachments(
    disaster_id: uuid.UUID,
    kind: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    svc.get_disaster(db, roles=_roles(user), disaster_id=disaster_id)
    items = svc.list_attachments(
        db, roles=_roles(user), disaster_id=disaster_id, kind=kind
    )
    return ok([_serialize_attachment(a) for a in items])


@router.post(
    "/{disaster_id}/attachments",
    status_code=201,
    summary="Register an attachment for a disaster",
    description=(
        "Register attachment metadata (fileName, fileUrl, kind, etc.). "
        "Upload storage is handled elsewhere. Requires `disaster:update`."
    ),
    response_model=None,
)
def create_disaster_attachment(
    disaster_id: uuid.UUID,
    payload: DisasterAttachmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    x = svc.register_attachment(
        db,
        roles=_roles(user),
        uploaded_by=user.id,
        disaster_id=disaster_id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="create", module="attachment", actor_id=user.id,
              entity_id=str(x.id), metadata={"disasterId": str(disaster_id)})
    return ok(_serialize_attachment(x))
