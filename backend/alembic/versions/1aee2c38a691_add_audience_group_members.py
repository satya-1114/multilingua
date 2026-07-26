"""add audience group members

Revision ID: 1aee2c38a691
Revises: 0b9f9b7455f7
Create Date: 2026-07-26 11:37:24.444667
"""

from alembic import op
import sqlalchemy as sa


revision = "1aee2c38a691"
down_revision = "0b9f9b7455f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audience_group_members",
        sa.Column("audience_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
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
            ["audience_id"],
            ["audience.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["audience_groups.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "audience_id",
            "group_id",
            name="uq_audience_group_member",
        ),
    )

    op.create_index(
        op.f("ix_audience_group_members_audience_id"),
        "audience_group_members",
        ["audience_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_audience_group_members_group_id"),
        "audience_group_members",
        ["group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_audience_group_members_group_id"),
        table_name="audience_group_members",
    )

    op.drop_index(
        op.f("ix_audience_group_members_audience_id"),
        table_name="audience_group_members",
    )

    op.drop_table("audience_group_members")