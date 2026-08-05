from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SendCampaignRequest(BaseModel):
    campaign_id: UUID
    channels: list[str] | None = None
    scheduled_at: datetime | None = None


class DeliveryResponse(BaseModel):
    id: UUID
    status: str
    channel: str


class DeliveryLogResponse(BaseModel):
    event: str
    success: bool
    message: str | None = None
    created_at: datetime