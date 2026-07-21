"""Multilingual content platform models (Phase 5.1 — DB foundation).

Reusable translation storage for any entity in the platform. Follows the
same layered conventions used by every other module (BaseMixin, UUID PKs,
JSONB metadata, soft delete, audit columns).

``entity_type`` + ``entity_id`` are a polymorphic pointer — no database-
level foreign key is declared because a translation may point at any of
several tables (disasters, public_resources, campaigns, organizations, …).
Referential integrity is enforced later in the service layer.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import BaseMixin


class Translation(BaseMixin, Base):
    """Per-field, per-locale translation for any polymorphic entity."""

    __tablename__ = "entity_translations"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "locale",
            "field_name",
            name="uq_entity_translations_scope",
        ),
        Index("ix_entity_translations_entity", "entity_type", "entity_id"),
        Index("ix_entity_translations_locale_status", "locale", "status"),
    )

    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    locale: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)

    translated_value: Mapped[str] = mapped_column(Text, nullable=False, default="")

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", index=True
    )
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    translated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    translator = relationship(
        "User", lazy="joined", foreign_keys=[translated_by_user_id]
    )
    reviewer = relationship(
        "User", lazy="joined", foreign_keys=[reviewed_by_user_id]
    )


class TranslationJob(BaseMixin, Base):
    """Tracks a translation request against a target entity + locale."""

    __tablename__ = "translation_jobs"
    __table_args__ = (
        Index("ix_translation_jobs_entity", "entity_type", "entity_id"),
        Index("ix_translation_jobs_target_locale", "target_locale"),
    )

    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    source_locale: Mapped[str] = mapped_column(String(20), nullable=False)
    target_locale: Mapped[str] = mapped_column(String(20), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)

    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    requester = relationship(
        "User", lazy="joined", foreign_keys=[requested_by_user_id]
    )


class TranslationLocale(BaseMixin, Base):
    """Supported language registry (single row per locale)."""

    __tablename__ = "translation_locales"
    __table_args__ = (
        UniqueConstraint("locale", name="uq_translation_locales_locale"),
        Index("ix_translation_locales_enabled", "enabled"),
    )

    locale: Mapped[str] = mapped_column(String(20), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    native_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rtl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_locale: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
