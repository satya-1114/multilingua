from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class AIPrompt(BaseMixin, Base):
    __tablename__ = "ai_prompts"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSONB, default=list)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)


class AIHistory(BaseMixin, Base):
    __tablename__ = "ai_history"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    mode: Mapped[str] = mapped_column(String(40), nullable=False, default="generate")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True, index=True)


class WorkspaceAiSettings(BaseMixin, Base):
    """Per-workspace AI provider configuration (encrypted API key)."""

    __tablename__ = "workspace_ai_settings"
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="gemini")
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    api_key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    project_id: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.4)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    auto_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_save: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_tone: Mapped[str] = mapped_column(String(40), nullable=False, default="professional")
    default_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")


class Translation(BaseMixin, Base):
    __tablename__ = "translations"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    quality: Mapped[float] = mapped_column(Numeric(4, 3), default=0)


class TranslationHistory(BaseMixin, Base):
    __tablename__ = "translation_history"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    translation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("translations.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
