"""Legacy automation stubs (retained for the legacy /automation API).

The full workflow engine lives in :mod:`app.models.workflow` (Phase 7.1).
These placeholder models keep the pre-existing ``/api/v1/automation``
router working without conflicting on table names.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class LegacyWorkflowDefinition(BaseMixin, Base):
    __tablename__ = "legacy_workflow_definitions"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    definition: Mapped[dict] = mapped_column(JSONB, default=dict)


class LegacyWorkflowExecution(BaseMixin, Base):
    __tablename__ = "legacy_workflow_executions"
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("legacy_workflow_definitions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="running")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
