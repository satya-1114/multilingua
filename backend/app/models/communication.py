from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class CommunicationChannel(BaseMixin, Base):
    __tablename__ = "communication_channels"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)


class Delivery(BaseMixin, Base):
    __tablename__ = "deliveries"
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)


class DeliveryRecipient(BaseMixin, Base):
    __tablename__ = "delivery_recipients"
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("deliveries.id", ondelete="CASCADE"), index=True)
    audience_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("audience.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RetryPolicy(BaseMixin, Base):
    __tablename__ = "retry_policies"
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    backoff_seconds: Mapped[int] = mapped_column(Integer, default=60)
    strategy: Mapped[str] = mapped_column(String(30), nullable=False, default="exponential")
