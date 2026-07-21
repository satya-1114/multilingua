"""Automation & Workflow Engine ORM models (Phase 7.1 — DB foundation).

Generic, module-agnostic orchestration primitives:

* ``WorkflowDefinition``    — reusable workflow blueprint.
* ``WorkflowTrigger``       — event/schedule/manual entry point.
* ``WorkflowAction``        — ordered step to execute after a trigger.
* ``WorkflowExecution``     — one execution instance of a definition.
* ``WorkflowExecutionStep`` — per-action execution record.

No FK dependencies on any domain module. ``organization_id`` is the
only optional cross-cutting reference.
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


# --------------------------------------------------------------------------- #
# WorkflowDefinition
# --------------------------------------------------------------------------- #


class WorkflowDefinition(BaseMixin, Base):
    """A reusable workflow blueprint."""

    __tablename__ = "workflow_definitions"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    triggers: Mapped[list["WorkflowTrigger"]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    actions: Mapped[list["WorkflowAction"]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="WorkflowAction.sequence",
    )
    executions: Mapped[list["WorkflowExecution"]] = relationship(
        back_populates="definition",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", name="uq_workflow_definitions_org_name"
        ),
        Index("ix_workflow_definitions_name", "name"),
        Index("ix_workflow_definitions_enabled", "enabled"),
    )


# --------------------------------------------------------------------------- #
# WorkflowTrigger
# --------------------------------------------------------------------------- #


class WorkflowTrigger(BaseMixin, Base):
    """An event/schedule/manual entry point for a workflow."""

    __tablename__ = "workflow_triggers"

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_name: Mapped[str] = mapped_column(String(120), nullable=False)
    event_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    conditions_json: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    definition: Mapped[WorkflowDefinition] = relationship(back_populates="triggers")

    __table_args__ = (
        Index("ix_workflow_triggers_event_name", "event_name"),
        Index("ix_workflow_triggers_event_source", "event_source"),
        Index("ix_workflow_triggers_definition", "workflow_definition_id"),
    )


# --------------------------------------------------------------------------- #
# WorkflowAction
# --------------------------------------------------------------------------- #


class WorkflowAction(BaseMixin, Base):
    """An ordered step to execute after a trigger fires."""

    __tablename__ = "workflow_actions"

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    configuration_json: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    definition: Mapped[WorkflowDefinition] = relationship(back_populates="actions")
    steps: Mapped[list["WorkflowExecutionStep"]] = relationship(
        back_populates="action",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "workflow_definition_id",
            "sequence",
            name="uq_workflow_actions_definition_sequence",
        ),
        Index(
            "ix_workflow_actions_definition_sequence",
            "workflow_definition_id",
            "sequence",
        ),
    )


# --------------------------------------------------------------------------- #
# WorkflowExecution
# --------------------------------------------------------------------------- #


class WorkflowExecution(BaseMixin, Base):
    """One execution instance of a workflow definition."""

    __tablename__ = "workflow_executions"

    workflow_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger_event: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_json: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    definition: Mapped[WorkflowDefinition] = relationship(back_populates="executions")
    steps: Mapped[list["WorkflowExecutionStep"]] = relationship(
        back_populates="execution",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_workflow_executions_status", "status"),
        Index("ix_workflow_executions_started_at", "started_at"),
        Index("ix_workflow_executions_definition", "workflow_definition_id"),
    )


# --------------------------------------------------------------------------- #
# WorkflowExecutionStep
# --------------------------------------------------------------------------- #


class WorkflowExecutionStep(BaseMixin, Base):
    """Per-action execution record for a WorkflowExecution."""

    __tablename__ = "workflow_execution_steps"

    workflow_execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_actions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_json: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )

    execution: Mapped[WorkflowExecution] = relationship(back_populates="steps")
    action: Mapped[WorkflowAction] = relationship(back_populates="steps")

    __table_args__ = (
        Index("ix_workflow_execution_steps_execution", "workflow_execution_id"),
        Index("ix_workflow_execution_steps_status", "status"),
    )
