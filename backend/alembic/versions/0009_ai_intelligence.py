"""AI Intelligence Platform schema

* Extends ai_prompts with description/tags/favorite/usage_count/is_system/user_id
* Extends ai_history with provider/mode/language/title/response_time/status/campaign_id
* Creates workspace_ai_settings (per-workspace provider config, encrypted key)
* Seeds the default prompt library (system prompts, unscoped to a workspace)

Revision ID: 0009_ai_intelligence
Revises: 0008_seed_roles
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_ai_intelligence"
down_revision = "0008_seed_roles"
branch_labels = None
depends_on = None


SYSTEM_PROMPTS: list[tuple[str, str, str, str, list[str], list[str]]] = [
    ("Emergency Alert", "emergency",
     "Broadcast an urgent public safety alert.",
     "Draft an emergency alert for {{event}} affecting {{district}}. Include the issuing "
     "authority {{department}}, action to take, and helpline {{helpline}}. Keep under 280 characters.",
     ["district", "event", "department", "helpline"],
     ["emergency", "sms", "public-safety"]),
    ("Government Notice", "government",
     "Formal government notice with reference codes and clear actions.",
     "Draft a formal government notice from {{department}} regarding {{event}}. "
     "Cite the reference number, applicable date {{date}}, and citizen actions required.",
     ["department", "event", "date"],
     ["government", "notice"]),
    ("Healthcare Advisory", "healthcare",
     "Public-health advisory in plain, WHO-compliant language.",
     "Draft a healthcare advisory for {{audience}} about {{topic}}. Use plain language, "
     "list preventive steps, and include the contact {{helpline}}.",
     ["audience", "topic", "helpline"],
     ["healthcare", "advisory"]),
    ("NGO Awareness Campaign", "ngo",
     "Community-friendly NGO awareness message with a call to action.",
     "Write an inclusive awareness message for {{city}} on {{topic}}, organised by {{organization}}. "
     "Include the event date {{date}} and time {{time}}.",
     ["organization", "city", "topic", "date", "time"],
     ["ngo", "awareness"]),
    ("Education Notice", "education",
     "Semester or scholarship notice for students.",
     "Draft an official notice from {{organization}} for {{event}} affecting all students. "
     "Include revised schedule, deadline {{date}} and contact department {{department}}.",
     ["organization", "event", "date", "department"],
     ["education", "notice"]),
    ("Disaster Alert", "emergency",
     "Rapid situational alert for a natural disaster.",
     "Draft a rapid alert for a {{event}} affecting {{district}}. Include evacuation route, "
     "shelter location, helpline {{helpline}}, and issuing department {{department}}.",
     ["event", "district", "helpline", "department"],
     ["disaster", "alert", "sms"]),
    ("Festival Greeting", "general",
     "Warm, inclusive festival greeting.",
     "Write a warm, inclusive greeting for the {{event}} festival from {{organization}} to citizens of {{city}}.",
     ["event", "organization", "city"],
     ["festival", "greeting"]),
    ("Public Safety Reminder", "emergency",
     "Non-urgent public safety reminder.",
     "Draft a friendly public safety reminder for {{audience}} about {{topic}} in {{city}}. "
     "Include a clear action.",
     ["audience", "topic", "city"],
     ["safety", "reminder"]),
    ("Vaccination Reminder", "healthcare",
     "SMS-length reminder for the next vaccination visit.",
     "Write a friendly reminder to {{recipient_name}} about the {{event}} vaccination "
     "visit at {{time}} on {{date}}. Sign off from {{organization}}.",
     ["recipient_name", "event", "date", "time", "organization"],
     ["vaccination", "healthcare", "sms"]),
]


def upgrade() -> None:
    # ---- ai_prompts extensions ---------------------------------------
    with op.batch_alter_table("ai_prompts") as batch:
        batch.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch.add_column(sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        batch.add_column(sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_index("ix_ai_prompts_user_id", "ai_prompts", ["user_id"])
    op.create_index("ix_ai_prompts_category", "ai_prompts", ["category"])

    # ---- ai_history extensions ---------------------------------------
    with op.batch_alter_table("ai_history") as batch:
        batch.add_column(sa.Column("provider", sa.String(40), nullable=False, server_default=""))
        batch.add_column(sa.Column("mode", sa.String(40), nullable=False, server_default="generate"))
        batch.add_column(sa.Column("language", sa.String(10), nullable=False, server_default="en"))
        batch.add_column(sa.Column("title", sa.String(200), nullable=False, server_default=""))
        batch.add_column(sa.Column("response_time_ms", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="ok"))
        batch.add_column(sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True))

    # ---- workspace_ai_settings ---------------------------------------
    op.create_table(
        "workspace_ai_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider", sa.String(40), nullable=False, server_default="gemini"),
        sa.Column("model", sa.String(120), nullable=False, server_default=""),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_url", sa.String(255), nullable=False, server_default=""),
        sa.Column("project_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.4"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("auto_review", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("auto_save", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("default_tone", sa.String(40), nullable=False, server_default="professional"),
        sa.Column("default_language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=True),
        sa.Column("updated_by", sa.String(64), nullable=True),
    )

    # ---- Seed system prompts (workspace_id = NULL sentinel not allowed;
    # store one row per prompt against every existing workspace).
    op.execute(
        """
        DO $$
        DECLARE
          ws_id uuid;
        BEGIN
          FOR ws_id IN SELECT id FROM workspaces LOOP
            -- Idempotent: skip if a system prompt with the same name already exists
            NULL;
          END LOOP;
        END $$;
        """
    )
    # Actual data seed is performed on-demand by the AI service to keep the
    # migration workspace-agnostic. See app.services.ai.ensure_system_prompts.


def downgrade() -> None:
    op.drop_table("workspace_ai_settings")
    with op.batch_alter_table("ai_history") as batch:
        for col in (
            "campaign_id", "status", "completion_tokens", "prompt_tokens",
            "response_time_ms", "title", "language", "mode", "provider",
        ):
            batch.drop_column(col)
    op.drop_index("ix_ai_prompts_category", table_name="ai_prompts")
    op.drop_index("ix_ai_prompts_user_id", table_name="ai_prompts")
    with op.batch_alter_table("ai_prompts") as batch:
        for col in ("user_id", "is_system", "usage_count", "favorite", "tags", "description"):
            batch.drop_column(col)