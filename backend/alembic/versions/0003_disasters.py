"""disaster management tables

Revision ID: 0003_disasters
Revises: 0002_volunteers
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "0003_disasters"
down_revision = "0002_volunteers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "disasters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("disaster_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="reported"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("district", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_disasters_disaster_type", "disasters", ["disaster_type"])
    op.create_index("ix_disasters_severity", "disasters", ["severity"])
    op.create_index("ix_disasters_status", "disasters", ["status"])
    op.create_index("ix_disasters_organization_id", "disasters", ["organization_id"])
    op.create_index("ix_disasters_city", "disasters", ["city"])
    op.create_index("ix_disasters_district", "disasters", ["district"])
    op.create_index("ix_disasters_state", "disasters", ["state"])
    op.create_index("ix_disasters_country", "disasters", ["country"])
    op.create_index("ix_disasters_started_at", "disasters", ["started_at"])
    op.create_index("ix_disasters_org_status", "disasters", ["organization_id", "status"])
    op.create_index("ix_disasters_type_status", "disasters", ["disaster_type", "status"])
    op.create_index("ix_disasters_severity_status", "disasters", ["severity", "status"])

    op.create_table(
        "disaster_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "disaster_id",
            UUID(as_uuid=True),
            sa.ForeignKey("disasters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "volunteer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("volunteers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("role", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="assigned"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.UniqueConstraint(
            "disaster_id", "volunteer_id", name="uq_disaster_assignment_volunteer"
        ),
    )
    op.create_index("ix_disaster_assignments_disaster_id", "disaster_assignments", ["disaster_id"])
    op.create_index("ix_disaster_assignments_volunteer_id", "disaster_assignments", ["volunteer_id"])
    op.create_index("ix_disaster_assignments_status", "disaster_assignments", ["status"])
    op.create_index(
        "ix_disaster_assignments_disaster_status",
        "disaster_assignments",
        ["disaster_id", "status"],
    )
    op.create_index(
        "ix_disaster_assignments_volunteer_status",
        "disaster_assignments",
        ["volunteer_id", "status"],
    )

    op.create_table(
        "disaster_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "disaster_id",
            UUID(as_uuid=True),
            sa.ForeignKey("disasters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=30), nullable=False, server_default="image"),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("caption", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_disaster_attachments_disaster_id", "disaster_attachments", ["disaster_id"])
    op.create_index(
        "ix_disaster_attachments_disaster_kind",
        "disaster_attachments",
        ["disaster_id", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_disaster_attachments_disaster_kind", table_name="disaster_attachments")
    op.drop_index("ix_disaster_attachments_disaster_id", table_name="disaster_attachments")
    op.drop_table("disaster_attachments")

    op.drop_index("ix_disaster_assignments_volunteer_status", table_name="disaster_assignments")
    op.drop_index("ix_disaster_assignments_disaster_status", table_name="disaster_assignments")
    op.drop_index("ix_disaster_assignments_status", table_name="disaster_assignments")
    op.drop_index("ix_disaster_assignments_volunteer_id", table_name="disaster_assignments")
    op.drop_index("ix_disaster_assignments_disaster_id", table_name="disaster_assignments")
    op.drop_table("disaster_assignments")

    for ix in (
        "ix_disasters_severity_status",
        "ix_disasters_type_status",
        "ix_disasters_org_status",
        "ix_disasters_started_at",
        "ix_disasters_country",
        "ix_disasters_state",
        "ix_disasters_district",
        "ix_disasters_city",
        "ix_disasters_organization_id",
        "ix_disasters_status",
        "ix_disasters_severity",
        "ix_disasters_disaster_type",
    ):
        op.drop_index(ix, table_name="disasters")
    op.drop_table("disasters")
