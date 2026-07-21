from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import BaseMixin


class Disaster(BaseMixin, Base):
    __tablename__ = "disasters"
    __table_args__ = (
        Index("ix_disasters_org_status", "organization_id", "status"),
        Index("ix_disasters_type_status", "disaster_type", "status"),
        Index("ix_disasters_severity_status", "severity", "status"),
        Index("ix_disasters_started_at", "started_at"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)

    disaster_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="reported", index=True
    )

    # Geolocation
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Reuse project JSONB convention (see AuditLog / AutomationExecution).
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    organization = relationship("Organization", lazy="joined")
    creator = relationship("User", lazy="joined", foreign_keys=[created_by_user_id])
    assignments: Mapped[list["DisasterAssignment"]] = relationship(
        "DisasterAssignment",
        back_populates="disaster",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    attachments: Mapped[list["DisasterAttachment"]] = relationship(
        "DisasterAttachment",
        back_populates="disaster",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DisasterAssignment(BaseMixin, Base):
    __tablename__ = "disaster_assignments"
    __table_args__ = (
        UniqueConstraint(
            "disaster_id", "volunteer_id", name="uq_disaster_assignment_volunteer"
        ),
        Index("ix_disaster_assignments_disaster_status", "disaster_id", "status"),
        Index("ix_disaster_assignments_volunteer_status", "volunteer_id", "status"),
    )

    disaster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disasters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    volunteer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("volunteers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="assigned", index=True
    )

    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    disaster = relationship("Disaster", back_populates="assignments", lazy="joined")
    volunteer = relationship("Volunteer", lazy="joined")


class DisasterAttachment(BaseMixin, Base):
    __tablename__ = "disaster_attachments"
    __table_args__ = (
        Index("ix_disaster_attachments_disaster_kind", "disaster_id", "kind"),
    )

    disaster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disasters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    kind: Mapped[str] = mapped_column(String(30), nullable=False, default="image")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    caption: Mapped[str | None] = mapped_column(String(500), nullable=True)

    disaster = relationship("Disaster", back_populates="attachments", lazy="joined")
