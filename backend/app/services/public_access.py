"""Public Information & QR business services.

Pure business layer: input validation, permission checks, slug/token
uniqueness, expiration handling, QR metadata lifecycle, and anonymous
view registration. Routers (Phase 4.3) translate DTOs and call these
functions. No FastAPI / HTTP concerns live here.
"""
from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.constants.public_access import (
    DEVICE_TYPES,
    QR_FORMAT_PNG,
    QR_FORMATS,
    QR_STATUS_ACTIVE,
    QR_STATUS_EXPIRED,
    QR_STATUS_PENDING,
    QR_STATUS_REVOKED,
    QR_STATUSES,
    RESOURCE_TYPES,
    VISIBILITIES,
    VISIBILITIES_RETRIEVABLE,
    VISIBILITY_DISABLED,
    VISIBILITY_EXPIRED,
    VISIBILITY_PRIVATE,
    VISIBILITY_PUBLIC,
)
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.models.public_access import PublicResource, PublicView, QRCode
from app.repositories.public_access import (
    public_resources,
    public_views,
    qr_codes,
)
from app.security.rbac import require_permission
from app.services import public_access_events as events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,118}[a-z0-9])?$")
_DUPLICATE_VIEW_WINDOW = timedelta(seconds=30)


def _is_past(dt: datetime | None) -> bool:
    if dt is None:
        return False
    aware = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return aware < datetime.now(timezone.utc)




def _as_uuid(value: uuid.UUID | str | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Invalid UUID: {value!r}") from exc


def _get_resource_or_404(
    db: Session, resource_id: uuid.UUID | str
) -> PublicResource:
    obj = public_resources.get(db, _as_uuid(resource_id))
    if obj is None:
        raise NotFoundError(
            "Public resource not found", details={"id": str(resource_id)}
        )
    return obj


def _get_qr_or_404(db: Session, qr_id: uuid.UUID | str) -> QRCode:
    obj = qr_codes.get(db, _as_uuid(qr_id))
    if obj is None:
        raise NotFoundError("QR code not found", details={"id": str(qr_id)})
    return obj


def _validate_slug(slug: str) -> None:
    if not slug or not _SLUG_RE.fullmatch(slug):
        raise ValidationError(
            "Invalid slug; must be lowercase alphanumerics and dashes",
            details={"slug": slug},
        )


def _ensure_unique_slug(
    db: Session, slug: str, *, exclude_id: uuid.UUID | None = None
) -> None:
    existing = public_resources.get_by_slug(db, slug)
    if existing is not None and existing.id != exclude_id:
        raise ConflictError("Slug already in use", details={"slug": slug})


def _ensure_unique_qr_token(
    db: Session, token: str, *, exclude_id: uuid.UUID | None = None
) -> None:
    existing = public_resources.get_by_qr_token(db, token)
    if existing is not None and existing.id != exclude_id:
        raise ConflictError("QR token already in use")


def _new_qr_token() -> str:
    # 32 hex chars — random, URL-safe, fits the 64-char column with headroom.
    return secrets.token_hex(16)


_ALIAS_MAP = {
    "resourceType": "resource_type",
    "resourceId": "resource_id",
    "qrToken": "qr_token",
    "expiresAt": "expires_at",
    "organizationId": "organization_id",
    "metadata": "metadata_",
    "publicResourceId": "public_resource_id",
    "generatedAt": "generated_at",
    "viewedAt": "viewed_at",
    "ipHash": "ip_hash",
    "userAgentHash": "user_agent_hash",
    "deviceType": "device_type",
}


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    for src, dst in _ALIAS_MAP.items():
        if src in data:
            data[dst] = data.pop(src)
    return data


def _hash_value(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# PublicResource service
# ---------------------------------------------------------------------------


def create_public_resource(
    db: Session,
    *,
    roles: Iterable[str],
    created_by: uuid.UUID | None,
    payload: dict[str, Any],
) -> PublicResource:
    require_permission(roles, "public:create")
    data = _normalize_payload(payload)

    resource_type = data.get("resource_type")
    if not resource_type:
        raise ValidationError("resourceType is required")
    if resource_type not in RESOURCE_TYPES:
        raise ValidationError(f"Invalid resource type: {resource_type}")

    if not data.get("title"):
        raise ValidationError("title is required")

    slug = data.get("slug")
    if not slug:
        raise ValidationError("slug is required")
    _validate_slug(slug)
    _ensure_unique_slug(db, slug)

    visibility = data.get("visibility") or VISIBILITY_PUBLIC
    if visibility not in VISIBILITIES:
        raise ValidationError(f"Invalid visibility: {visibility}")
    data["visibility"] = visibility

    expires_at = data.get("expires_at")
    if _is_past(expires_at):
        raise ValidationError("expiresAt must be in the future")

    for key in ("organization_id", "resource_id"):
        if data.get(key) is not None:
            data[key] = _as_uuid(data[key])

    data["created_by_user_id"] = created_by
    data.setdefault("metadata_", {})
    # No QR token by default; call regenerate_qr_token to mint one.
    resource = public_resources.create(db, data)
    events.resource_created(db, resource)
    return resource


def update_public_resource(
    db: Session,
    *,
    roles: Iterable[str],
    resource_id: uuid.UUID | str,
    payload: dict[str, Any],
) -> PublicResource:
    require_permission(roles, "public:update")
    resource = _get_resource_or_404(db, resource_id)
    data = _normalize_payload(payload)

    if "slug" in data and data["slug"] is not None:
        _validate_slug(data["slug"])
        _ensure_unique_slug(db, data["slug"], exclude_id=resource.id)

    if "visibility" in data and data["visibility"] is not None:
        if data["visibility"] not in VISIBILITIES:
            raise ValidationError(f"Invalid visibility: {data['visibility']}")

    if "expires_at" in data and data["expires_at"] is not None:
        if _is_past(data["expires_at"]):
            raise ValidationError("expiresAt must be in the future")

    if "organization_id" in data and data["organization_id"] is not None:
        data["organization_id"] = _as_uuid(data["organization_id"])

    # Immutable via this endpoint — use dedicated regenerate_* helpers.
    data.pop("qr_token", None)
    data.pop("resource_type", None)
    data.pop("resource_id", None)

    updated = public_resources.update(db, resource, data)
    events.resource_updated(db, updated)
    return updated


def publish_public_resource(
    db: Session, *, roles: Iterable[str], resource_id: uuid.UUID | str
) -> PublicResource:
    require_permission(roles, "public:manage")
    resource = _get_resource_or_404(db, resource_id)
    if _is_past(resource.expires_at):
        raise ConflictError(
            "Cannot publish an expired resource",
            details={"expiresAt": resource.expires_at.isoformat()},
        )
    updated = public_resources.update(db, resource, {"visibility": VISIBILITY_PUBLIC})
    events.resource_published(db, updated)
    return updated


def unpublish_public_resource(
    db: Session,
    *,
    roles: Iterable[str],
    resource_id: uuid.UUID | str,
    to: str = VISIBILITY_PRIVATE,
) -> PublicResource:
    require_permission(roles, "public:manage")
    if to not in (VISIBILITY_PRIVATE, VISIBILITY_DISABLED):
        raise ValidationError(f"Invalid target visibility: {to}")
    resource = _get_resource_or_404(db, resource_id)
    updated = public_resources.update(db, resource, {"visibility": to})
    events.resource_unpublished(db, updated)
    return updated


def expire_public_resource(
    db: Session, *, roles: Iterable[str], resource_id: uuid.UUID | str
) -> PublicResource:
    require_permission(roles, "public:manage")
    resource = _get_resource_or_404(db, resource_id)
    now = datetime.now(timezone.utc)
    updated = public_resources.update(
        db,
        resource,
        {"visibility": VISIBILITY_EXPIRED, "expires_at": now},
    )
    # Deactivate any live QR codes for the resource.
    qr_codes.deactivate_previous(
        db, updated.id, new_status=QR_STATUS_EXPIRED
    )
    events.resource_expired(db, updated)
    return updated


def regenerate_qr_token(
    db: Session, *, roles: Iterable[str], resource_id: uuid.UUID | str
) -> PublicResource:
    require_permission(roles, "qr:manage")
    resource = _get_resource_or_404(db, resource_id)
    token = _new_qr_token()
    # Extremely unlikely collision, but keep the guarantee.
    _ensure_unique_qr_token(db, token, exclude_id=resource.id)
    # Existing active QR codes reference the previous token; revoke them.
    qr_codes.deactivate_previous(
        db, resource.id, new_status=QR_STATUS_REVOKED
    )
    updated = public_resources.update(db, resource, {"qr_token": token})
    events.qr_token_regenerated(db, updated)
    return updated


def regenerate_slug(
    db: Session,
    *,
    roles: Iterable[str],
    resource_id: uuid.UUID | str,
    slug: str,
) -> PublicResource:
    require_permission(roles, "public:update")
    resource = _get_resource_or_404(db, resource_id)
    _validate_slug(slug)
    _ensure_unique_slug(db, slug, exclude_id=resource.id)
    updated = public_resources.update(db, resource, {"slug": slug})
    events.slug_regenerated(db, updated)
    return updated


def get_public_resource(
    db: Session, *, roles: Iterable[str], resource_id: uuid.UUID | str
) -> PublicResource:
    require_permission(roles, "public:view")
    return _get_resource_or_404(db, resource_id)


def list_resources(
    db: Session, *, roles: Iterable[str], filters: dict[str, Any]
) -> tuple[list[PublicResource], int]:
    require_permission(roles, "public:view")
    return public_resources.search(db, **filters)


# -- Anonymous retrieval (called from a public API in Phase 4.3) -------------


def resolve_public_by_slug(db: Session, slug: str) -> PublicResource:
    """Anonymous read. Raises NotFound / Forbidden / Conflict."""
    resource = public_resources.get_by_slug(db, slug)
    if resource is None:
        raise NotFoundError("Public resource not found", details={"slug": slug})
    _ensure_retrievable(resource)
    return resource


def resolve_public_by_qr_token(db: Session, token: str) -> PublicResource:
    resource = public_resources.get_by_qr_token(db, token)
    if resource is None:
        raise NotFoundError("Public resource not found")
    _ensure_retrievable(resource)
    return resource


def _ensure_retrievable(resource: PublicResource) -> None:
    if resource.visibility not in VISIBILITIES_RETRIEVABLE:
        raise ForbiddenError(
            "Resource is not publicly retrievable",
            details={"visibility": resource.visibility},
        )
    if _is_past(resource.expires_at):
        raise ConflictError(
            "Resource has expired",
            details={"expiresAt": resource.expires_at.isoformat()},
        )


# ---------------------------------------------------------------------------
# QRCode service (metadata only — no image generation)
# ---------------------------------------------------------------------------


def create_qr_metadata(
    db: Session,
    *,
    roles: Iterable[str],
    resource_id: uuid.UUID | str,
    payload: dict[str, Any],
) -> QRCode:
    require_permission(roles, "qr:create")
    resource = _get_resource_or_404(db, resource_id)

    data = _normalize_payload(payload)
    fmt = data.get("format") or QR_FORMAT_PNG
    if fmt not in QR_FORMATS:
        raise ValidationError(f"Invalid QR format: {fmt}")

    version = data.get("version", 1)
    if not isinstance(version, int) or version < 1 or version > 40:
        raise ValidationError("QR version must be an integer in [1, 40]")

    # Ensure the resource has a QR token to embed; mint one on first use.
    if not resource.qr_token:
        token = _new_qr_token()
        _ensure_unique_qr_token(db, token)
        resource = public_resources.update(db, resource, {"qr_token": token})

    qr = qr_codes.create(
        db,
        {
            "public_resource_id": resource.id,
            "format": fmt,
            "version": version,
            "status": QR_STATUS_PENDING,
            "metadata_": data.get("metadata_") or {},
        },
    )
    events.qr_created(db, qr)
    return qr


def activate_qr(
    db: Session, *, roles: Iterable[str], qr_id: uuid.UUID | str
) -> QRCode:
    require_permission(roles, "qr:manage")
    qr = _get_qr_or_404(db, qr_id)
    if qr.status == QR_STATUS_ACTIVE:
        return qr
    if qr.status in (QR_STATUS_REVOKED, QR_STATUS_EXPIRED):
        raise ConflictError(
            "Cannot activate a revoked/expired QR",
            details={"status": qr.status},
        )
    # Mark any currently-active QR for the same resource as revoked.
    qr_codes.deactivate_previous(
        db, qr.public_resource_id, new_status=QR_STATUS_REVOKED
    )
    updated = qr_codes.update(
        db,
        qr,
        {
            "status": QR_STATUS_ACTIVE,
            "generated_at": datetime.now(timezone.utc),
        },
    )
    events.qr_activated(db, updated)
    return updated


def deactivate_qr(
    db: Session,
    *,
    roles: Iterable[str],
    qr_id: uuid.UUID | str,
    status: str = QR_STATUS_REVOKED,
) -> QRCode:
    require_permission(roles, "qr:manage")
    if status not in (QR_STATUS_REVOKED, QR_STATUS_EXPIRED):
        raise ValidationError(f"Invalid deactivation status: {status}")
    qr = _get_qr_or_404(db, qr_id)
    if qr.status == status:
        return qr
    updated = qr_codes.update(db, qr, {"status": status})
    events.qr_deactivated(db, updated)
    return updated


def regenerate_qr_metadata(
    db: Session,
    *,
    roles: Iterable[str],
    qr_id: uuid.UUID | str,
    payload: dict[str, Any] | None = None,
) -> QRCode:
    """Create a fresh QR metadata row and revoke the previous one."""
    require_permission(roles, "qr:manage")
    prev = _get_qr_or_404(db, qr_id)
    data = _normalize_payload(payload or {})
    fmt = data.get("format") or prev.format
    version = data.get("version") or prev.version
    if fmt not in QR_FORMATS:
        raise ValidationError(f"Invalid QR format: {fmt}")
    if not isinstance(version, int) or version < 1 or version > 40:
        raise ValidationError("QR version must be an integer in [1, 40]")

    qr_codes.deactivate_previous(
        db, prev.public_resource_id, new_status=QR_STATUS_REVOKED
    )
    if prev.status != QR_STATUS_REVOKED:
        qr_codes.update(db, prev, {"status": QR_STATUS_REVOKED})

    fresh = qr_codes.create(
        db,
        {
            "public_resource_id": prev.public_resource_id,
            "format": fmt,
            "version": version,
            "status": QR_STATUS_PENDING,
            "metadata_": data.get("metadata_") or {},
        },
    )
    events.qr_regenerated(db, fresh)
    return fresh


def list_qr_codes(
    db: Session,
    *,
    roles: Iterable[str],
    resource_id: uuid.UUID | str,
    status: str | None = None,
) -> list[QRCode]:
    require_permission(roles, "qr:view")
    if status and status not in QR_STATUSES:
        raise ValidationError(f"Invalid QR status: {status}")
    return qr_codes.list_by_resource(db, _as_uuid(resource_id), status=status)


# ---------------------------------------------------------------------------
# PublicView service
# ---------------------------------------------------------------------------


def register_view(
    db: Session,
    *,
    resource_id: uuid.UUID | str,
    ip: str | None = None,
    user_agent: str | None = None,
    country: str | None = None,
    device_type: str | None = None,
    referrer: str | None = None,
    viewed_at: datetime | None = None,
) -> PublicView | None:
    """Anonymous view registration.

    - Raw IP / User-Agent are hashed with SHA-256 before persistence.
    - Rapid duplicate refreshes from the same fingerprint within
      ``_DUPLICATE_VIEW_WINDOW`` are suppressed and return ``None``.
    - The target resource must be publicly retrievable.
    """
    resource = _get_resource_or_404(db, resource_id)
    _ensure_retrievable(resource)

    if device_type and device_type not in DEVICE_TYPES:
        raise ValidationError(f"Invalid device type: {device_type}")
    if country and len(country) != 2:
        raise ValidationError("country must be an ISO-2 code")
    if referrer and len(referrer) > 1024:
        referrer = referrer[:1024]

    ip_hash = _hash_value(ip)
    ua_hash = _hash_value(user_agent)

    recent = public_views.recent_matching_view(
        db,
        public_resource_id=resource.id,
        ip_hash=ip_hash,
        user_agent_hash=ua_hash,
        within=_DUPLICATE_VIEW_WINDOW,
    )
    if recent is not None:
        return None

    return public_views.create(
        db,
        {
            "public_resource_id": resource.id,
            "viewed_at": viewed_at or datetime.now(timezone.utc),
            "ip_hash": ip_hash,
            "user_agent_hash": ua_hash,
            "country": country,
            "device_type": device_type,
            "referrer": referrer,
        },
    )


def summarize_views(
    db: Session,
    *,
    roles: Iterable[str],
    resource_id: uuid.UUID | str,
    since: datetime | None = None,
) -> dict[str, Any]:
    require_permission(roles, "public:view")
    rid = _as_uuid(resource_id)
    return {
        "total": public_views.count_views(db, rid, since=since),
        "byCountry": public_views.summarize_by_country(db, rid),
        "byDevice": public_views.summarize_by_device(db, rid),
    }


def list_views(
    db: Session,
    *,
    roles: Iterable[str],
    resource_id: uuid.UUID | str,
    limit: int = 100,
) -> list[PublicView]:
    require_permission(roles, "public:view")
    return public_views.list_by_resource(db, _as_uuid(resource_id), limit=limit)


__all__ = [
    "create_public_resource",
    "update_public_resource",
    "publish_public_resource",
    "unpublish_public_resource",
    "expire_public_resource",
    "regenerate_qr_token",
    "regenerate_slug",
    "get_public_resource",
    "list_resources",
    "resolve_public_by_slug",
    "resolve_public_by_qr_token",
    "create_qr_metadata",
    "activate_qr",
    "deactivate_qr",
    "regenerate_qr_metadata",
    "list_qr_codes",
    "register_view",
    "summarize_views",
    "list_views",
]
