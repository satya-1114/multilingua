"""public information & qr metadata tables

Revision ID: 0004_public_access
Revises: 0003_disasters
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "0004_public_access"
down_revision = "0003_disasters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_resources",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("resource_type", sa.String(length=40), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("qr_token", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="public"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("slug", name="uq_public_resources_slug"),
        sa.UniqueConstraint("qr_token", name="uq_public_resources_qr_token"),
    )
    op.create_index("ix_public_resources_resource_type", "public_resources", ["resource_type"])
    op.create_index("ix_public_resources_resource_id", "public_resources", ["resource_id"])
    op.create_index("ix_public_resources_visibility", "public_resources", ["visibility"])
    op.create_index("ix_public_resources_expires_at", "public_resources", ["expires_at"])
    op.create_index("ix_public_resources_organization_id", "public_resources", ["organization_id"])
    op.create_index(
        "ix_public_resources_resource", "public_resources", ["resource_type", "resource_id"]
    )
    op.create_index(
        "ix_public_resources_org_visibility",
        "public_resources",
        ["organization_id", "visibility"],
    )
    op.create_index(
        "ix_public_resources_visibility_expires",
        "public_resources",
        ["visibility", "expires_at"],
    )

    op.create_table(
        "qr_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "public_resource_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public_resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(length=10), nullable=False, server_default="png"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_qr_codes_public_resource_id", "qr_codes", ["public_resource_id"])
    op.create_index("ix_qr_codes_status", "qr_codes", ["status"])
    op.create_index(
        "ix_qr_codes_resource_status", "qr_codes", ["public_resource_id", "status"]
    )

    op.create_table(
        "public_views",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "public_resource_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public_resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("device_type", sa.String(length=20), nullable=True),
        sa.Column("referrer", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_public_views_public_resource_id", "public_views", ["public_resource_id"])
    op.create_index("ix_public_views_viewed_at", "public_views", ["viewed_at"])
    op.create_index(
        "ix_public_views_resource_viewed", "public_views", ["public_resource_id", "viewed_at"]
    )
    op.create_index("ix_public_views_country", "public_views", ["country"])


def downgrade() -> None:
    op.drop_index("ix_public_views_country", table_name="public_views")
    op.drop_index("ix_public_views_resource_viewed", table_name="public_views")
    op.drop_index("ix_public_views_viewed_at", table_name="public_views")
    op.drop_index("ix_public_views_public_resource_id", table_name="public_views")
    op.drop_table("public_views")

    op.drop_index("ix_qr_codes_resource_status", table_name="qr_codes")
    op.drop_index("ix_qr_codes_status", table_name="qr_codes")
    op.drop_index("ix_qr_codes_public_resource_id", table_name="qr_codes")
    op.drop_table("qr_codes")

    for ix in (
        "ix_public_resources_visibility_expires",
        "ix_public_resources_org_visibility",
        "ix_public_resources_resource",
        "ix_public_resources_organization_id",
        "ix_public_resources_expires_at",
        "ix_public_resources_visibility",
        "ix_public_resources_resource_id",
        "ix_public_resources_resource_type",
    ):
        op.drop_index(ix, table_name="public_resources")
    op.drop_table("public_resources")
