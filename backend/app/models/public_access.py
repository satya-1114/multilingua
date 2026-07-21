"""Public Information & QR models (Phase 4.1 — DB foundation).

Persistence for publicly shareable resource pointers, QR metadata, and
anonymous view tracking. Follows the same layered conventions used by the
Volunteer and Disaster modules (BaseMixin, UUID PKs, JSONB metadata, soft
delete, audit columns). No repository/service/API/frontend in this phase.

``resource_id`` is a loose FK — it stores the target row id but no
database-level foreign key is declared, because a ``PublicResource`` may
point at any of several tables (disasters, campaigns, organizations, …).
Referential integrity is enforced in the service layer once introduced.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import BaseMixin


class PublicResource(BaseMixin, Base):
    __tablename__ = "public_resources"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_public_resources_slug"),
        UniqueConstraint("qr_token", name="uq_public_resources_qr_token"),
        Index(
            "ix_public_resources_resource",
            "resource_type",
            "resource_id",
        ),
        Index(
            "ix_public_resources_org_visibility",
            "organization_id",
            "visibility",
        ),
        Index("ix_public_resources_visibility_expires", "visibility", "expires_at"),
    )

    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    qr_token: Mapped[str | None] = mapped_column(String(64), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)

    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public", index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Free-form settings (theme, share text overrides, contact info, …).
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    organization = relationship("Organization", lazy="joined")
    creator = relationship("User", lazy="joined", foreign_keys=[created_by_user_id])

    qr_codes: Mapped[list["QRCode"]] = relationship(
        "QRCode",
        back_populates="public_resource",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    views: Mapped[list["PublicView"]] = relationship(
        "PublicView",
        back_populates="public_resource",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class QRCode(BaseMixin, Base):
    """Metadata about generated QR codes. Image bytes live outside the DB."""

    __tablename__ = "qr_codes"
    __table_args__ = (
        Index(
            "ix_qr_codes_resource_status",
            "public_resource_id",
            "status",
        ),
    )

    public_resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public_resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    format: Mapped[str] = mapped_column(String(10), nullable=False, default="png")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )

    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    public_resource = relationship(
        "PublicResource", back_populates="qr_codes", lazy="joined"
    )


class PublicView(BaseMixin, Base):
    """Anonymous access log for public resources. IP / UA are hashed."""

    __tablename__ = "public_views"
    __table_args__ = (
        Index("ix_public_views_resource_viewed", "public_resource_id", "viewed_at"),
        Index("ix_public_views_country", "country"),
    )

    public_resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public_resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    viewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    public_resource = relationship(
        "PublicResource", back_populates="views", lazy="joined"
    )
