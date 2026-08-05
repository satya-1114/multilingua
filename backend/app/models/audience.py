from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class Audience(BaseMixin, Base):
    __tablename__ = "audience"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)


class AudienceGroup(BaseMixin, Base):
    __tablename__ = "audience_groups"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class AudienceTag(BaseMixin, Base):
    __tablename__ = "audience_tags"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#64748b")


class AudienceGroupMember(BaseMixin, Base):
    """Many-to-many link between Audience and AudienceGroup."""

    __tablename__ = "audience_group_members"

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "audience_id",
            name="uq_audience_group_member",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audience_groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    audience_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audience.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )