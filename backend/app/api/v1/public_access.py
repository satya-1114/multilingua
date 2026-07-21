"""Public Information & QR management routes (authenticated).

Thin FastAPI layer over :mod:`app.services.public_access`. All business
logic (validation, permissions, lifecycle, slug/token uniqueness) lives
in the service layer.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.public_access import PublicResource, PublicView, QRCode
from app.models.user import User
from app.schemas.public_access import (
    PublicResourceCreate,
    PublicResourceUpdate,
    QRCodeCreate,
)
from app.services import audit
from app.services import public_access as svc

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _roles(user: User) -> list[str]:
    return [r.name for r in getattr(user, "roles", []) or []]


def _serialize_resource(r: PublicResource) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "resourceType": r.resource_type,
        "resourceId": str(r.resource_id) if r.resource_id else None,
        "slug": r.slug,
        "qrToken": r.qr_token,
        "title": r.title,
        "description": r.description,
        "visibility": r.visibility,
        "expiresAt": _iso(r.expires_at),
        "organizationId": str(r.organization_id) if r.organization_id else None,
        "createdByUserId": str(r.created_by_user_id) if r.created_by_user_id else None,
        "metadata": dict(r.metadata_ or {}),
        "createdAt": _iso(r.created_at),
        "updatedAt": _iso(r.updated_at),
    }


def _serialize_qr(q: QRCode) -> dict[str, Any]:
    return {
        "id": str(q.id),
        "publicResourceId": str(q.public_resource_id),
        "format": q.format,
        "version": q.version,
        "status": q.status,
        "generatedAt": _iso(q.generated_at),
        "metadata": dict(q.metadata_ or {}),
        "createdAt": _iso(q.created_at),
        "updatedAt": _iso(q.updated_at),
    }


def _serialize_view(v: PublicView) -> dict[str, Any]:
    return {
        "id": str(v.id),
        "publicResourceId": str(v.public_resource_id),
        "viewedAt": _iso(v.viewed_at),
        "ipHash": v.ip_hash,
        "userAgentHash": v.user_agent_hash,
        "country": v.country,
        "deviceType": v.device_type,
        "referrer": v.referrer,
    }


# ---------------------------------------------------------------------------
# QR literal routes  (registered BEFORE parameterized /{resource_id}/*)
# ---------------------------------------------------------------------------


@router.patch("/qr/{qr_id}/activate", response_model=None, summary="Activate a QR code")
def activate_qr(
    qr_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    q = svc.activate_qr(db, roles=_roles(user), qr_id=qr_id)
    audit.log(db, action="activate", module="qr_code", actor_id=user.id,
              entity_id=str(q.id), entity_label=q.format,
              metadata={"resourceId": str(q.public_resource_id)})
    return ok(_serialize_qr(q))


@router.patch("/qr/{qr_id}/deactivate", response_model=None, summary="Deactivate a QR code")
def deactivate_qr(
    qr_id: uuid.UUID,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    status = (payload or {}).get("status") if isinstance(payload, dict) else None
    kwargs: dict[str, Any] = {"roles": _roles(user), "qr_id": qr_id}
    if status:
        kwargs["status"] = status
    q = svc.deactivate_qr(db, **kwargs)
    audit.log(db, action="deactivate", module="qr_code", actor_id=user.id,
              entity_id=str(q.id), entity_label=q.status,
              metadata={"resourceId": str(q.public_resource_id)})
    return ok(_serialize_qr(q))


@router.patch("/qr/{qr_id}/regenerate", response_model=None, summary="Regenerate QR metadata")
def regenerate_qr(
    qr_id: uuid.UUID,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    q = svc.regenerate_qr_metadata(
        db, roles=_roles(user), qr_id=qr_id, payload=payload or {}
    )
    audit.log(db, action="regenerate", module="qr_code", actor_id=user.id,
              entity_id=str(q.id), entity_label=q.format,
              metadata={"resourceId": str(q.public_resource_id), "previousQrId": str(qr_id)})
    return ok(_serialize_qr(q))


# ---------------------------------------------------------------------------
# Public resource list / create
# ---------------------------------------------------------------------------


@router.get("", response_model=None, summary="List public resources")
def list_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200, alias="pageSize"),
    search: str | None = Query(None, max_length=200),
    resource_type: str | None = Query(None, alias="resourceType"),
    visibility: str | None = None,
    organization_id: uuid.UUID | None = Query(None, alias="organizationId"),
    resource_id: uuid.UUID | None = Query(None, alias="resourceId"),
    active_only: bool | None = Query(None, alias="activeOnly"),
    sort_by: str | None = Query(None, alias="sortBy", max_length=64),
    sort_dir: str = Query("desc", alias="sortDir", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    filters = {
        "page": page,
        "page_size": page_size,
        "search": search,
        "resource_type": resource_type,
        "visibility": visibility,
        "organization_id": organization_id,
        "resource_id": resource_id,
        "active_only": active_only,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
    }
    items, total = svc.list_resources(db, roles=_roles(user), filters=filters)
    return paginated(
        [_serialize_resource(r) for r in items], page, page_size, total
    )


@router.post("", status_code=201, response_model=None, summary="Create a public resource")
def create_resource(
    payload: PublicResourceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    r = svc.create_public_resource(
        db,
        roles=_roles(user),
        created_by=user.id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="create", module="public_resource", actor_id=user.id,
              entity_id=str(r.id), entity_label=r.title,
              metadata={"slug": r.slug, "resourceType": r.resource_type})
    return ok(_serialize_resource(r))


# ---------------------------------------------------------------------------
# Per-resource routes
# ---------------------------------------------------------------------------


@router.get("/{resource_id}", response_model=None, summary="Get a public resource")
def get_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    r = svc.get_public_resource(db, roles=_roles(user), resource_id=resource_id)
    return ok(_serialize_resource(r))


@router.patch("/{resource_id}", response_model=None, summary="Update a public resource")
def update_resource(
    resource_id: uuid.UUID,
    payload: PublicResourceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    r = svc.update_public_resource(
        db,
        roles=_roles(user),
        resource_id=resource_id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="update", module="public_resource", actor_id=user.id,
              entity_id=str(r.id), entity_label=r.title)
    return ok(_serialize_resource(r))


@router.post("/{resource_id}/publish", response_model=None, summary="Publish a resource")
def publish_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    r = svc.publish_public_resource(db, roles=_roles(user), resource_id=resource_id)
    audit.log(db, action="publish", module="public_resource", actor_id=user.id,
              entity_id=str(r.id), entity_label=r.title)
    return ok(_serialize_resource(r))


@router.post("/{resource_id}/unpublish", response_model=None, summary="Unpublish a resource")
def unpublish_resource(
    resource_id: uuid.UUID,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    to = (payload or {}).get("to") if isinstance(payload, dict) else None
    kwargs: dict[str, Any] = {"roles": _roles(user), "resource_id": resource_id}
    if to:
        kwargs["to"] = to
    r = svc.unpublish_public_resource(db, **kwargs)
    audit.log(db, action="unpublish", module="public_resource", actor_id=user.id,
              entity_id=str(r.id), entity_label=r.title,
              metadata={"visibility": r.visibility})
    return ok(_serialize_resource(r))


@router.post("/{resource_id}/expire", response_model=None, summary="Expire a resource")
def expire_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    r = svc.expire_public_resource(db, roles=_roles(user), resource_id=resource_id)
    audit.log(db, action="expire", module="public_resource", actor_id=user.id,
              entity_id=str(r.id), entity_label=r.title)
    return ok(_serialize_resource(r))


@router.post("/{resource_id}/regenerate-slug", response_model=None, summary="Regenerate resource slug")
def regenerate_slug(
    resource_id: uuid.UUID,
    payload: dict[str, Any] = Body(..., examples=[{"slug": "new-slug"}]),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    slug = (payload or {}).get("slug")
    r = svc.regenerate_slug(
        db, roles=_roles(user), resource_id=resource_id, slug=slug
    )
    audit.log(db, action="regenerate_slug", module="public_resource", actor_id=user.id,
              entity_id=str(r.id), entity_label=r.title, metadata={"slug": r.slug})
    return ok(_serialize_resource(r))


@router.post("/{resource_id}/regenerate-qr-token", response_model=None, summary="Regenerate QR token")
def regenerate_qr_token(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    r = svc.regenerate_qr_token(db, roles=_roles(user), resource_id=resource_id)
    audit.log(db, action="regenerate_qr_token", module="public_resource", actor_id=user.id,
              entity_id=str(r.id), entity_label=r.title)
    return ok(_serialize_resource(r))


# ---------- QR listing / creation for a resource ---------------------------


@router.get("/{resource_id}/qr", response_model=None, summary="List QR codes for a resource")
def list_qr_codes(
    resource_id: uuid.UUID,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    items = svc.list_qr_codes(
        db, roles=_roles(user), resource_id=resource_id, status=status
    )
    return ok([_serialize_qr(q) for q in items])


@router.post(
    "/{resource_id}/qr",
    status_code=201,
    response_model=None,
    summary="Register QR metadata for a resource",
)
def create_qr(
    resource_id: uuid.UUID,
    payload: QRCodeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    q = svc.create_qr_metadata(
        db,
        roles=_roles(user),
        resource_id=resource_id,
        payload=payload.model_dump(exclude_none=True),
    )
    audit.log(db, action="create", module="qr_code", actor_id=user.id,
              entity_id=str(q.id), entity_label=q.format,
              metadata={"resourceId": str(resource_id), "version": q.version})
    return ok(_serialize_qr(q))


# ---------- Views ----------------------------------------------------------


@router.get("/{resource_id}/views", response_model=None, summary="List recent views")
def list_views(
    resource_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    items = svc.list_views(
        db, roles=_roles(user), resource_id=resource_id, limit=limit
    )
    return ok([_serialize_view(v) for v in items])


@router.get(
    "/{resource_id}/views/summary",
    response_model=None,
    summary="Aggregate view counts",
)
def views_summary(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    data = svc.summarize_views(
        db, roles=_roles(user), resource_id=resource_id
    )
    return ok(data)
