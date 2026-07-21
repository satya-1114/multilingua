"""Public Information & QR domain-event emitters.

Thin adapter that translates PublicResource / QRCode business events into
the existing :mod:`app.services.notifications` pipeline. Kept isolated
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
from app.models.public_access import PublicResource, QRCode
from app.runtime.events import publish_event
from app.services import notifications as notif_service

log = get_logger(__name__)

CATEGORY = "public_access"


def _safe_create(
    db: Session, *, user_id: uuid.UUID | str | None, **kwargs: Any
) -> None:
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
        log.warning("public_access notification emit failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


def _title(r: PublicResource) -> str:
    return r.title or f"Resource {r.id}"


def _href(r: PublicResource) -> str:
    return f"/public-resources/{r.id}"


def _notify_owner(
    db: Session,
    resource: PublicResource,
    *,
    title: str,
    message: str,
    priority: str = "normal",
) -> None:
    _safe_create(
        db,
        user_id=resource.created_by_user_id,
        title=title,
        message=message,
        priority=priority,
        href=_href(resource),
    )


# ---------------------------------------------------------------------------
# PublicResource lifecycle
# ---------------------------------------------------------------------------


def resource_created(db: Session, resource: PublicResource) -> None:
    _notify_owner(
        db, resource,
        title=f"Public resource created: {_title(resource)}",
        message="Your public resource has been created.",
    )
    publish_event(
        "public_resource.created",
        db=db,
        organization_id=getattr(resource, "organization_id", None),
        actor_id=getattr(resource, "created_by_user_id", None),
        resource_type="public_resource",
        resource_id=resource.id,
        payload={"slug": getattr(resource, "slug", None)},
    )


def resource_updated(db: Session, resource: PublicResource) -> None:
    _notify_owner(
        db, resource,
        title=f"Public resource updated: {_title(resource)}",
        message="Your public resource has been updated.",
        priority="low",
    )


def resource_published(db: Session, resource: PublicResource) -> None:
    _notify_owner(
        db, resource,
        title=f"Published: {_title(resource)}",
        message="This resource is now publicly accessible.",
    )
    publish_event(
        "public_resource.published",
        db=db,
        organization_id=getattr(resource, "organization_id", None),
        actor_id=getattr(resource, "created_by_user_id", None),
        resource_type="public_resource",
        resource_id=resource.id,
        payload={"slug": getattr(resource, "slug", None)},
    )


def resource_unpublished(db: Session, resource: PublicResource) -> None:
    _notify_owner(
        db, resource,
        title=f"Unpublished: {_title(resource)}",
        message="This resource is no longer publicly accessible.",
    )


def resource_expired(db: Session, resource: PublicResource) -> None:
    _notify_owner(
        db, resource,
        title=f"Expired: {_title(resource)}",
        message="This resource has been marked as expired.",
        priority="low",
    )


def slug_regenerated(db: Session, resource: PublicResource) -> None:
    _notify_owner(
        db, resource,
        title=f"Slug regenerated: {_title(resource)}",
        message="The public slug for this resource has changed.",
    )


def qr_token_regenerated(db: Session, resource: PublicResource) -> None:
    _notify_owner(
        db, resource,
        title=f"QR token regenerated: {_title(resource)}",
        message="A new QR token has been minted; previous QR codes were revoked.",
        priority="high",
    )


# ---------------------------------------------------------------------------
# QRCode lifecycle
# ---------------------------------------------------------------------------


def _notify_qr_owner(
    db: Session,
    qr: QRCode,
    *,
    title: str,
    message: str,
    priority: str = "normal",
) -> None:
    resource = getattr(qr, "public_resource", None)
    user_id = getattr(resource, "created_by_user_id", None) if resource else None
    href = _href(resource) if resource else f"/public-resources/qr/{qr.id}"
    _safe_create(
        db,
        user_id=user_id,
        title=title,
        message=message,
        priority=priority,
        href=href,
    )


def qr_created(db: Session, qr: QRCode) -> None:
    _notify_qr_owner(
        db, qr,
        title="QR code registered",
        message=f"A new QR code ({qr.format}, v{qr.version}) has been registered.",
        priority="low",
    )
    publish_event(
        "public_resource.qr_created",
        db=db,
        resource_type="qr_code",
        resource_id=qr.id,
        payload={
            "format": qr.format,
            "version": qr.version,
            "publicResourceId": str(getattr(qr, "public_resource_id", "")) or None,
        },
    )


def qr_activated(db: Session, qr: QRCode) -> None:
    _notify_qr_owner(
        db, qr,
        title="QR code activated",
        message="A QR code is now active for this resource.",
    )


def qr_deactivated(db: Session, qr: QRCode) -> None:
    _notify_qr_owner(
        db, qr,
        title="QR code deactivated",
        message=f"A QR code has been marked as {qr.status}.",
    )


def qr_regenerated(db: Session, qr: QRCode) -> None:
    _notify_qr_owner(
        db, qr,
        title="QR code regenerated",
        message="A fresh QR metadata row has been minted; the previous one was revoked.",
        priority="high",
    )


__all__ = [
    "CATEGORY",
    "resource_created",
    "resource_updated",
    "resource_published",
    "resource_unpublished",
    "resource_expired",
    "slug_regenerated",
    "qr_token_regenerated",
    "qr_created",
    "qr_activated",
    "qr_deactivated",
    "qr_regenerated",
]
