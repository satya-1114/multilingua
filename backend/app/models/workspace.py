from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class Workspace(BaseMixin, Base):
    __tablename__ = "workspaces"
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(40), nullable=False, default="growth")
    region: Mapped[str] = mapped_column(String(60), nullable=False, default="ap-south-1")
    timezone: Mapped[str] = mapped_column(String(60), nullable=False, default="Asia/Kolkata")
    primary_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    storage_quota_gb: Mapped[int] = mapped_column(Integer, default=100)
    api_quota_monthly: Mapped[int] = mapped_column(Integer, default=1_000_000)
    member_count: Mapped[int] = mapped_column(Integer, default=0)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="viewer")
