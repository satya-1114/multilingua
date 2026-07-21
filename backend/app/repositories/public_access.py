"""Repository layer for the Public Information & QR module.

Thin extensions over :class:`CRUDBase`. Business rules (validation,
permission checks, hashing) live in :mod:`app.services.public_access`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants.public_access import (
    QR_STATUS_ACTIVE,
    VISIBILITIES_RETRIEVABLE,
    VISIBILITY_PUBLIC,
)
from app.crud.base import CRUDBase
from app.models.public_access import PublicResource, PublicView, QRCode


# ---------------------------------------------------------------------------
# PublicResource
# ---------------------------------------------------------------------------


class PublicResourceRepository(CRUDBase[PublicResource]):
    def __init__(self) -> None:
        super().__init__(PublicResource)

    def get_by_slug(self, db: Session, slug: str) -> PublicResource | None:
        stmt = select(PublicResource).where(
            PublicResource.slug == slug,
            PublicResource.deleted_at.is_(None),
        )
        return db.scalar(stmt)

    def get_by_qr_token(self, db: Session, qr_token: str) -> PublicResource | None:
        stmt = select(PublicResource).where(
            PublicResource.qr_token == qr_token,
            PublicResource.deleted_at.is_(None),
        )
        return db.scalar(stmt)

    def list_public(
        self,
        db: Session,
        *,
        resource_type: str | None = None,
        limit: int | None = None,
    ) -> list[PublicResource]:
        stmt = select(PublicResource).where(
            PublicResource.visibility == VISIBILITY_PUBLIC,
            PublicResource.deleted_at.is_(None),
        )
        if resource_type:
            stmt = stmt.where(PublicResource.resource_type == resource_type)
        stmt = stmt.order_by(PublicResource.created_at.desc())
        if limit:
            stmt = stmt.limit(limit)
        return list(db.scalars(stmt))

    def list_by_resource(
        self,
        db: Session,
        *,
        resource_type: str,
        resource_id: uuid.UUID | str,
    ) -> list[PublicResource]:
        stmt = select(PublicResource).where(
            PublicResource.resource_type == resource_type,
            PublicResource.resource_id == resource_id,
            PublicResource.deleted_at.is_(None),
        )
        return list(db.scalars(stmt.order_by(PublicResource.created_at.desc())))

    def list_by_organization(
        self, db: Session, organization_id: uuid.UUID | str
    ) -> list[PublicResource]:
        stmt = select(PublicResource).where(
            PublicResource.organization_id == organization_id,
            PublicResource.deleted_at.is_(None),
        )
        return list(db.scalars(stmt.order_by(PublicResource.created_at.desc())))

    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
        resource_type: str | None = None,
        visibility: str | None = None,
        organization_id: uuid.UUID | str | None = None,
        resource_id: uuid.UUID | str | None = None,
        active_only: bool | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[PublicResource], int]:
        stmt = select(PublicResource).where(PublicResource.deleted_at.is_(None))
        if resource_type:
            stmt = stmt.where(PublicResource.resource_type == resource_type)
        if visibility:
            stmt = stmt.where(PublicResource.visibility == visibility)
        if organization_id:
            stmt = stmt.where(PublicResource.organization_id == organization_id)
        if resource_id:
            stmt = stmt.where(PublicResource.resource_id == resource_id)
        if active_only:
            now = datetime.now(timezone.utc)
            stmt = stmt.where(
                PublicResource.visibility.in_(list(VISIBILITIES_RETRIEVABLE)),
                or_(
                    PublicResource.expires_at.is_(None),
                    PublicResource.expires_at > now,
                ),
            )
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    PublicResource.title.ilike(like),
                    PublicResource.description.ilike(like),
                    PublicResource.slug.ilike(like),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(PublicResource, sort_by):
            col = getattr(PublicResource, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(PublicResource.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)


# ---------------------------------------------------------------------------
# QRCode
# ---------------------------------------------------------------------------


class QRCodeRepository(CRUDBase[QRCode]):
    def __init__(self) -> None:
        super().__init__(QRCode)

    def list_by_resource(
        self,
        db: Session,
        public_resource_id: uuid.UUID | str,
        *,
        status: str | None = None,
    ) -> list[QRCode]:
        stmt = select(QRCode).where(
            QRCode.public_resource_id == public_resource_id,
            QRCode.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(QRCode.status == status)
        return list(db.scalars(stmt.order_by(QRCode.created_at.desc())))

    def latest_active(
        self, db: Session, public_resource_id: uuid.UUID | str
    ) -> QRCode | None:
        stmt = (
            select(QRCode)
            .where(
                QRCode.public_resource_id == public_resource_id,
                QRCode.status == QR_STATUS_ACTIVE,
                QRCode.deleted_at.is_(None),
            )
            .order_by(QRCode.created_at.desc())
            .limit(1)
        )
        return db.scalar(stmt)

    def deactivate_previous(
        self,
        db: Session,
        public_resource_id: uuid.UUID | str,
        *,
        new_status: str,
    ) -> int:
        """Mark every currently-active QR for a resource as ``new_status``.

        Returns the number of rows updated. Caller is expected to commit
        (``CRUDBase.create``/``update`` commits on the next mutation).
        """
        rows = list(
            db.scalars(
                select(QRCode).where(
                    QRCode.public_resource_id == public_resource_id,
                    QRCode.status == QR_STATUS_ACTIVE,
                    QRCode.deleted_at.is_(None),
                )
            )
        )
        for row in rows:
            row.status = new_status
        if rows:
            db.commit()
        return len(rows)


# ---------------------------------------------------------------------------
# PublicView
# ---------------------------------------------------------------------------


class PublicViewRepository(CRUDBase[PublicView]):
    def __init__(self) -> None:
        super().__init__(PublicView)

    def list_by_resource(
        self,
        db: Session,
        public_resource_id: uuid.UUID | str,
        *,
        limit: int = 100,
    ) -> list[PublicView]:
        stmt = (
            select(PublicView)
            .where(
                PublicView.public_resource_id == public_resource_id,
                PublicView.deleted_at.is_(None),
            )
            .order_by(PublicView.viewed_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt))

    def count_views(
        self,
        db: Session,
        public_resource_id: uuid.UUID | str,
        *,
        since: datetime | None = None,
    ) -> int:
        stmt = select(func.count(PublicView.id)).where(
            PublicView.public_resource_id == public_resource_id,
            PublicView.deleted_at.is_(None),
        )
        if since:
            stmt = stmt.where(PublicView.viewed_at >= since)
        return int(db.scalar(stmt) or 0)

    def summarize_by_country(
        self, db: Session, public_resource_id: uuid.UUID | str
    ) -> dict[str, int]:
        stmt = (
            select(PublicView.country, func.count(PublicView.id))
            .where(
                PublicView.public_resource_id == public_resource_id,
                PublicView.deleted_at.is_(None),
            )
            .group_by(PublicView.country)
        )
        return {row[0] or "unknown": int(row[1]) for row in db.execute(stmt)}

    def summarize_by_device(
        self, db: Session, public_resource_id: uuid.UUID | str
    ) -> dict[str, int]:
        stmt = (
            select(PublicView.device_type, func.count(PublicView.id))
            .where(
                PublicView.public_resource_id == public_resource_id,
                PublicView.deleted_at.is_(None),
            )
            .group_by(PublicView.device_type)
        )
        return {row[0] or "unknown": int(row[1]) for row in db.execute(stmt)}

    def recent_matching_view(
        self,
        db: Session,
        *,
        public_resource_id: uuid.UUID | str,
        ip_hash: str | None,
        user_agent_hash: str | None,
        within: timedelta,
    ) -> PublicView | None:
        """Used by services to suppress duplicate rapid refreshes."""
        if ip_hash is None and user_agent_hash is None:
            return None
        since = datetime.now(timezone.utc) - within
        stmt = (
            select(PublicView)
            .where(
                PublicView.public_resource_id == public_resource_id,
                PublicView.viewed_at >= since,
                PublicView.deleted_at.is_(None),
            )
            .order_by(PublicView.viewed_at.desc())
            .limit(1)
        )
        if ip_hash is not None:
            stmt = stmt.where(PublicView.ip_hash == ip_hash)
        if user_agent_hash is not None:
            stmt = stmt.where(PublicView.user_agent_hash == user_agent_hash)
        return db.scalar(stmt)


public_resources = PublicResourceRepository()
qr_codes = QRCodeRepository()
public_views = PublicViewRepository()


__all__ = [
    "PublicResourceRepository",
    "QRCodeRepository",
    "PublicViewRepository",
    "public_resources",
    "qr_codes",
    "public_views",
]
