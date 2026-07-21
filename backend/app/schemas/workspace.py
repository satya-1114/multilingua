from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import IdentifiedDto


class WorkspaceDto(IdentifiedDto):
    name: str
    slug: str
    plan: str
    region: str
    memberCount: int = 0


class WorkspaceCreate(BaseModel):
    organizationId: str
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=120)
    plan: str = "growth"
    region: str = "ap-south-1"
    timezone: str = "Asia/Kolkata"
    primaryLanguage: str = "en"


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None
    region: str | None = None
    timezone: str | None = None
    primaryLanguage: str | None = None
