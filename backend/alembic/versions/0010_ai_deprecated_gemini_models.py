"""Migrate deprecated Gemini model ids in workspace_ai_settings.

Google retired several Gemini model ids for new API keys (notably
``gemini-2.5-flash``, ``gemini-2.5-flash-lite`` and the ``gemini-1.x`` family). Workspaces saved
with those ids keep pinning the runtime to a dead model, overriding
``settings.GEMINI_MODEL``. Clear the column so downstream resolution
falls back to the current platform default.

Revision ID: 0010_ai_deprecated_gemini_models
Revises: 0009_ai_intelligence
"""
from __future__ import annotations

from alembic import op

revision = "0010_ai_deprecated_gemini_models"
down_revision = "0009_ai_intelligence"
branch_labels = None
depends_on = None


_DEPRECATED = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "models/gemini-2.5-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-pro",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-pro",
    "models/gemini-1.0-pro",
)


def upgrade() -> None:
    op.execute(
        """
        UPDATE workspace_ai_settings
           SET model = ''
         WHERE lower(provider) = 'gemini'
           AND model IN ({values})
        """.format(values=", ".join(f"'{m}'" for m in _DEPRECATED))
    )


def downgrade() -> None:
    # Irreversible on purpose — restoring a deprecated model id would
    # re-break AI generation.
    pass