from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id", name="uq_favorite"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    target_type: Mapped[str] = mapped_column(String(60), primary_key=True)
    target_id: Mapped[str] = mapped_column(String(64), primary_key=True)


class UserPreference(BaseMixin, Base):
    __tablename__ = "user_preferences"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)


class HelpArticle(BaseMixin, Base):
    __tablename__ = "help_articles"
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="general")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")


class KnowledgeArticle(BaseMixin, Base):
    __tablename__ = "knowledge_articles"
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tags: Mapped[list] = mapped_column(JSONB, default=list)
