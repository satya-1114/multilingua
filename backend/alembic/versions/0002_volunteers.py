"""volunteer module tables

Revision ID: 0002_volunteers
Revises: 0001_initial
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID


revision = "0002_volunteers"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "volunteers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("languages", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("skills", ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("current_location", sa.String(length=255), nullable=True),
        sa.Column("availability", sa.String(length=60), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="available"),
        sa.Column("emergency_contact_name", sa.String(length=160), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(length=64), nullable=True),
        sa.Column("emergency_contact_relation", sa.String(length=60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("user_id", name="uq_volunteer_user"),
    )
    op.create_index("ix_volunteers_user_id", "volunteers", ["user_id"])
    op.create_index("ix_volunteers_organization_id", "volunteers", ["organization_id"])
    op.create_index("ix_volunteers_status", "volunteers", ["status"])

    op.create_table(
        "volunteer_tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("volunteer_id", UUID(as_uuid=True), sa.ForeignKey("volunteers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_volunteer_tasks_volunteer_id", "volunteer_tasks", ["volunteer_id"])
    op.create_index("ix_volunteer_tasks_campaign_id", "volunteer_tasks", ["campaign_id"])
    op.create_index("ix_volunteer_tasks_status", "volunteer_tasks", ["status"])
    op.create_index("ix_volunteer_tasks_volunteer_status", "volunteer_tasks", ["volunteer_id", "status"])
    op.create_index("ix_volunteer_tasks_campaign_status", "volunteer_tasks", ["campaign_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_volunteer_tasks_campaign_status", table_name="volunteer_tasks")
    op.drop_index("ix_volunteer_tasks_volunteer_status", table_name="volunteer_tasks")
    op.drop_index("ix_volunteer_tasks_status", table_name="volunteer_tasks")
    op.drop_index("ix_volunteer_tasks_campaign_id", table_name="volunteer_tasks")
    op.drop_index("ix_volunteer_tasks_volunteer_id", table_name="volunteer_tasks")
    op.drop_table("volunteer_tasks")

    op.drop_index("ix_volunteers_status", table_name="volunteers")
    op.drop_index("ix_volunteers_organization_id", table_name="volunteers")
    op.drop_index("ix_volunteers_user_id", table_name="volunteers")
    op.drop_table("volunteers")
