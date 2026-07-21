"""multilingual content platform tables

Revision ID: 0005_translation
Revises: 0004_public_access
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "0005_translation"
down_revision = "0004_public_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- entity_translations --------------------------------------------------
    op.create_table(
        "entity_translations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("locale", sa.String(length=20), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("translated_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "translated_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by_user_id",
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
        sa.UniqueConstraint(
            "entity_type", "entity_id", "locale", "field_name",
            name="uq_entity_translations_scope",
        ),
    )
    op.create_index(
        "ix_entity_translations_entity_type", "entity_translations", ["entity_type"]
    )
    op.create_index(
        "ix_entity_translations_entity_id", "entity_translations", ["entity_id"]
    )
    op.create_index("ix_entity_translations_locale", "entity_translations", ["locale"])
    op.create_index("ix_entity_translations_status", "entity_translations", ["status"])
    op.create_index(
        "ix_entity_translations_entity",
        "entity_translations",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_entity_translations_locale_status",
        "entity_translations",
        ["locale", "status"],
    )

    # -- translation_jobs -----------------------------------------------------
    op.create_table(
        "translation_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_locale", sa.String(length=20), nullable=False),
        sa.Column("target_locale", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column(
            "requested_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_translation_jobs_entity", "translation_jobs", ["entity_type", "entity_id"]
    )
    op.create_index("ix_translation_jobs_status", "translation_jobs", ["status"])
    op.create_index(
        "ix_translation_jobs_target_locale", "translation_jobs", ["target_locale"]
    )

    # -- translation_locales --------------------------------------------------
    op.create_table(
        "translation_locales",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("locale", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("native_name", sa.String(length=120), nullable=True),
        sa.Column("rtl", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "default_locale", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("locale", name="uq_translation_locales_locale"),
    )
    op.create_index(
        "ix_translation_locales_enabled", "translation_locales", ["enabled"]
    )


def downgrade() -> None:
    op.drop_index("ix_translation_locales_enabled", table_name="translation_locales")
    op.drop_table("translation_locales")

    op.drop_index("ix_translation_jobs_target_locale", table_name="translation_jobs")
    op.drop_index("ix_translation_jobs_status", table_name="translation_jobs")
    op.drop_index("ix_translation_jobs_entity", table_name="translation_jobs")
    op.drop_table("translation_jobs")

    op.drop_index("ix_entity_translations_locale_status", table_name="entity_translations")
    op.drop_index("ix_entity_translations_entity", table_name="entity_translations")
    op.drop_index("ix_entity_translations_status", table_name="entity_translations")
    op.drop_index("ix_entity_translations_locale", table_name="entity_translations")
    op.drop_index("ix_entity_translations_entity_id", table_name="entity_translations")
    op.drop_index("ix_entity_translations_entity_type", table_name="entity_translations")
    op.drop_table("entity_translations")
