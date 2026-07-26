"""communication hub

Revision ID: 0b9f9b7455f7
Revises: 0010_ai_deprecated_gemini_models
Create Date: 2026-07-26 01:36:13.694023
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0b9f9b7455f7'
down_revision = '0010_ai_deprecated_gemini_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_logs",
        sa.Column("delivery_id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=True),
        sa.Column("event", sa.String(length=50), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "provider_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["delivery_id"],
            ["deliveries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["delivery_recipients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_delivery_logs_delivery_id"),
        "delivery_logs",
        ["delivery_id"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index(
        op.f("ix_delivery_logs_delivery_id"),
        table_name="delivery_logs",
    )

    op.drop_table("delivery_logs")
