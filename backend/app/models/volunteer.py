from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import BaseMixin


class Volunteer(BaseMixin, Base):
    __tablename__ = "volunteers"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_volunteer_user"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    languages: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    current_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    availability: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="available", index=True
    )

    emergency_contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emergency_contact_relation: Mapped[str | None] = mapped_column(String(60), nullable=True)

    user = relationship("User", lazy="joined")
    organization = relationship("Organization", lazy="joined")
    tasks: Mapped[list["VolunteerTask"]] = relationship(
        "VolunteerTask",
        back_populates="volunteer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class VolunteerTask(BaseMixin, Base):
    __tablename__ = "volunteer_tasks"
    __table_args__ = (
        Index("ix_volunteer_tasks_volunteer_status", "volunteer_id", "status"),
        Index("ix_volunteer_tasks_campaign_status", "campaign_id", "status"),
    )

    volunteer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("volunteers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)

    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    volunteer = relationship("Volunteer", back_populates="tasks", lazy="joined")
    campaign = relationship("Campaign", lazy="joined")
