from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import IdentifiedDto


class ChannelDto(IdentifiedDto):
    kind: str
    name: str
    provider: str
    enabled: bool


class DeliveryDto(IdentifiedDto):
    campaignId: str
    channel: str
    status: str
    scheduledAt: datetime | None = None
    attempts: int = 0


class DeliveryReceiptDto(IdentifiedDto):
    deliveryId: str
    audienceId: str
    status: str
    deliveredAt: datetime | None = None
    errorMessage: str | None = None


class RetryPolicyDto(IdentifiedDto):
    channel: str
    maxAttempts: int
    backoffSeconds: int
    strategy: str


class ScheduleRequest(BaseModel):
    campaignId: str
    channel: str
    scheduledAt: datetime | None = None
    priority: int = 5
