"""automation & workflow engine tables

Revision ID: 0007_workflow
Revises: 0006_analytics
Create Date: 2026-07-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "0007_workflow"
down_revision = "0006_analytics"
branch_labels = None
depends_on = None


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
    ]


def upgrade() -> None:
    # -- workflow_definitions ------------------------------------------------
    op.create_table(
        "workflow_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        *_base_columns(),
        sa.UniqueConstraint(
            "organization_id", "name", name="uq_workflow_definitions_org_name"
        ),
    )
    op.create_index(
        "ix_workflow_definitions_name", "workflow_definitions", ["name"]
    )
    op.create_index(
        "ix_workflow_definitions_enabled", "workflow_definitions", ["enabled"]
    )

    # -- workflow_triggers ---------------------------------------------------
    op.create_table(
        "workflow_triggers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_definition_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("event_source", sa.String(length=120), nullable=True),
        sa.Column(
            "conditions_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        *_base_columns(),
    )
    op.create_index(
        "ix_workflow_triggers_event_name", "workflow_triggers", ["event_name"]
    )
    op.create_index(
        "ix_workflow_triggers_event_source", "workflow_triggers", ["event_source"]
    )
    op.create_index(
        "ix_workflow_triggers_definition",
        "workflow_triggers",
        ["workflow_definition_id"],
    )

    # -- workflow_actions ----------------------------------------------------
    op.create_table(
        "workflow_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_definition_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column(
            "configuration_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        *_base_columns(),
        sa.UniqueConstraint(
            "workflow_definition_id",
            "sequence",
            name="uq_workflow_actions_definition_sequence",
        ),
        sa.CheckConstraint("sequence > 0", name="ck_workflow_actions_sequence_positive"),
    )
    op.create_index(
        "ix_workflow_actions_definition_sequence",
        "workflow_actions",
        ["workflow_definition_id", "sequence"],
    )

    # -- workflow_executions -------------------------------------------------
    op.create_table(
        "workflow_executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_definition_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trigger_event", sa.String(length=120), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "context_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        *_base_columns(),
    )
    op.create_index(
        "ix_workflow_executions_status", "workflow_executions", ["status"]
    )
    op.create_index(
        "ix_workflow_executions_started_at",
        "workflow_executions",
        ["started_at"],
    )
    op.create_index(
        "ix_workflow_executions_definition",
        "workflow_executions",
        ["workflow_definition_id"],
    )

    # -- workflow_execution_steps -------------------------------------------
    op.create_table(
        "workflow_execution_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_execution_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_action_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_actions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "retry_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "output_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        *_base_columns(),
        sa.CheckConstraint(
            "retry_count >= 0",
            name="ck_workflow_execution_steps_retry_nonneg",
        ),
    )
    op.create_index(
        "ix_workflow_execution_steps_execution",
        "workflow_execution_steps",
        ["workflow_execution_id"],
    )
    op.create_index(
        "ix_workflow_execution_steps_status",
        "workflow_execution_steps",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_execution_steps_status", table_name="workflow_execution_steps"
    )
    op.drop_index(
        "ix_workflow_execution_steps_execution",
        table_name="workflow_execution_steps",
    )
    op.drop_table("workflow_execution_steps")

    op.drop_index(
        "ix_workflow_executions_definition", table_name="workflow_executions"
    )
    op.drop_index(
        "ix_workflow_executions_started_at", table_name="workflow_executions"
    )
    op.drop_index("ix_workflow_executions_status", table_name="workflow_executions")
    op.drop_table("workflow_executions")

    op.drop_index(
        "ix_workflow_actions_definition_sequence", table_name="workflow_actions"
    )
    op.drop_table("workflow_actions")

    op.drop_index(
        "ix_workflow_triggers_definition", table_name="workflow_triggers"
    )
    op.drop_index(
        "ix_workflow_triggers_event_source", table_name="workflow_triggers"
    )
    op.drop_index(
        "ix_workflow_triggers_event_name", table_name="workflow_triggers"
    )
    op.drop_table("workflow_triggers")

    op.drop_index(
        "ix_workflow_definitions_enabled", table_name="workflow_definitions"
    )
    op.drop_index("ix_workflow_definitions_name", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")
