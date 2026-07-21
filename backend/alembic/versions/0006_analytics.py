"""analytics & reporting platform tables

Revision ID: 0006_analytics
Revises: 0005_translation
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "0006_analytics"
down_revision = "0005_translation"
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
    # -- analytics_metrics ---------------------------------------------------
    op.create_table(
        "analytics_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_name", sa.String(length=120), nullable=False),
        sa.Column("metric_scope", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metric_value",
            sa.Numeric(20, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("metric_unit", sa.String(length=40), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        *_base_columns(),
    )
    op.create_index("ix_analytics_metrics_scope", "analytics_metrics", ["metric_scope"])
    op.create_index(
        "ix_analytics_metrics_entity",
        "analytics_metrics",
        ["entity_type", "entity_id"],
    )
    op.create_index("ix_analytics_metrics_name", "analytics_metrics", ["metric_name"])
    op.create_index(
        "ix_analytics_metrics_recorded_at", "analytics_metrics", ["recorded_at"]
    )

    # -- analytics_snapshots -------------------------------------------------
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_type", sa.String(length=20), nullable=False),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metrics_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        *_base_columns(),
    )
    op.create_index(
        "ix_analytics_snapshots_type", "analytics_snapshots", ["snapshot_type"]
    )
    op.create_index(
        "ix_analytics_snapshots_period",
        "analytics_snapshots",
        ["period_start", "period_end"],
    )

    # -- analytics_reports ---------------------------------------------------
    op.create_table(
        "analytics_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("report_name", sa.String(length=200), nullable=False),
        sa.Column("report_type", sa.String(length=40), nullable=False),
        sa.Column(
            "requested_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        *_base_columns(),
    )
    op.create_index("ix_analytics_reports_status", "analytics_reports", ["status"])
    op.create_index(
        "ix_analytics_reports_generated_at", "analytics_reports", ["generated_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_reports_generated_at", table_name="analytics_reports")
    op.drop_index("ix_analytics_reports_status", table_name="analytics_reports")
    op.drop_table("analytics_reports")

    op.drop_index("ix_analytics_snapshots_period", table_name="analytics_snapshots")
    op.drop_index("ix_analytics_snapshots_type", table_name="analytics_snapshots")
    op.drop_table("analytics_snapshots")

    op.drop_index("ix_analytics_metrics_recorded_at", table_name="analytics_metrics")
    op.drop_index("ix_analytics_metrics_name", table_name="analytics_metrics")
    op.drop_index("ix_analytics_metrics_entity", table_name="analytics_metrics")
    op.drop_index("ix_analytics_metrics_scope", table_name="analytics_metrics")
    op.drop_table("analytics_metrics")
