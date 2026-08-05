from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List
from uuid import UUID


class CampaignAudienceRequest(BaseModel):
    audienceIds: List[UUID] = Field(..., min_items=1)


class CampaignTemplateRequest(BaseModel):
    templateId: UUID
    channel: str


class CampaignAudienceItem(BaseModel):
    id: UUID
    fullName: str | None = None
    email: str | None = None
    phone: str | None = None


class CampaignTemplateItem(BaseModel):
    templateId: UUID
    channel: str
