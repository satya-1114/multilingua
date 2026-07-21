"""Anonymous Public Access endpoints.

These routes intentionally do NOT require authentication. They only expose
publicly retrievable resources and accept anonymous view registration.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.public_access import _serialize_resource, _serialize_view
from app.core.responses import ok
from app.dependencies.db import get_db
from app.services import audit
from app.services import public_access as svc

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def _register(
    request: Request,
    payload: dict[str, Any] | None,
    db: Session,
    resource_id,
):
    body = payload or {}
    view = svc.register_view(
        db,
        resource_id=resource_id,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        country=body.get("country"),
        device_type=body.get("deviceType") or body.get("device_type"),
        referrer=body.get("referrer") or request.headers.get("referer"),
    )
    if view is None:
        return ok({"registered": False, "reason": "duplicate"})
    # Aggregate-safe audit only: no IP / UA / referrer / user PII.
    try:
        audit.log(
            db,
            action="view",
            module="public_view",
            actor_id=None,
            entity_id=str(resource_id),
            entity_label=None,
            metadata={
                "country": view.country,
                "deviceType": view.device_type,
            },
        )
    except Exception:
        pass
    return ok({"registered": True, "view": _serialize_view(view)})


@router.get("/p/{slug}", response_model=None, summary="Resolve a resource by slug")
def resolve_by_slug(slug: str, db: Session = Depends(get_db)):
    r = svc.resolve_public_by_slug(db, slug)
    return ok(_serialize_resource(r))


@router.get("/q/{qr_token}", response_model=None, summary="Resolve a resource by QR token")
def resolve_by_qr(qr_token: str, db: Session = Depends(get_db)):
    r = svc.resolve_public_by_qr_token(db, qr_token)
    return ok(_serialize_resource(r))


@router.post("/p/{slug}/view", response_model=None, summary="Register an anonymous view (by slug)")
def register_view_by_slug(
    slug: str,
    request: Request,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
):
    r = svc.resolve_public_by_slug(db, slug)
    return _register(request, payload, db, r.id)


@router.post("/q/{qr_token}/view", response_model=None, summary="Register an anonymous view (by QR)")
def register_view_by_qr(
    qr_token: str,
    request: Request,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
):
    r = svc.resolve_public_by_qr_token(db, qr_token)
    return _register(request, payload, db, r.id)
