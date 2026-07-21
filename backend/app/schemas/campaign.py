from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import IdentifiedDto


class CampaignDto(IdentifiedDto):
    name: str
    status: str
    channels: list[str] = Field(default_factory=list)
    audienceCount: int = 0
    startsAt: datetime | None = None
    endsAt: datetime | None = None


class CampaignCreate(BaseModel):
    workspaceId: str
    name: str = Field(min_length=1, max_length=200)
    channels: list[str] = Field(default_factory=list)
    startsAt: datetime | None = None
    endsAt: datetime | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    channels: list[str] | None = None
    startsAt: datetime | None = None
    endsAt: datetime | None = None
