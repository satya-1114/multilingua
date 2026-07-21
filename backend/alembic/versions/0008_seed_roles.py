"""seed default platform roles

Populates the `roles` table with the canonical set of RBAC roles used by
the platform. Idempotent: uses INSERT ... WHERE NOT EXISTS keyed on the
unique `name` column, so re-running migrations never creates duplicates.

Revision ID: 0008_seed_roles
Revises: 0007_workflow
Create Date: 2026-07-21
"""
from __future__ import annotations

from alembic import op


revision = "0008_seed_roles"
down_revision = "0007_workflow"
branch_labels = None
depends_on = None


# (name, description) — kept in sync with app.security.rbac.PERMISSIONS keys.
DEFAULT_ROLES: list[tuple[str, str]] = [
    ("super_admin", "Full platform access"),
    ("org_admin", "Organization administrator"),
    ("automation_admin", "Manages workflow automation"),
    ("campaign_manager", "Plans and launches campaigns"),
    ("content_creator", "Drafts campaign content"),
    ("communication_officer", "Coordinates delivery and channels"),
    ("data_analyst", "Reads analytics and reports"),
    ("translator", "Translates content across supported locales"),
    ("reviewer", "Reviews and publishes translated content"),
    ("volunteer", "Field volunteer — acts on assigned tasks"),
    ("viewer", "Read-only access"),
]


def upgrade() -> None:
    for name, description in DEFAULT_ROLES:
        safe_name = name.replace("'", "''")
        safe_desc = description.replace("'", "''")
        op.execute(
            f"""
            INSERT INTO roles (id, name, description, created_at, updated_at)
            SELECT gen_random_uuid(), '{safe_name}', '{safe_desc}', now(), now()
            WHERE NOT EXISTS (SELECT 1 FROM roles WHERE name = '{safe_name}')
            """
        )


def downgrade() -> None:
    # Best-effort: remove only rows we would have inserted, and only when
    # no user still references them (avoid breaking existing assignments).
    names = ", ".join(f"'{n}'" for n, _ in DEFAULT_ROLES)
    op.execute(
        f"""
        DELETE FROM roles
        WHERE name IN ({names})
          AND id NOT IN (SELECT role_id FROM user_roles)
        """
    )