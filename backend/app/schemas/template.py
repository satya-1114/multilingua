from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import IdentifiedDto


class TemplateDto(IdentifiedDto):
    name: str
    category: str
    channels: list[str] = Field(default_factory=list)
    language: str
    version: int
    status: str


class TemplateCreate(BaseModel):
    workspaceId: str
    name: str = Field(min_length=1, max_length=200)
    category: str = "general"
    channels: list[str] = Field(default_factory=list)
    language: str = "en"
    body: str = ""


class TemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    channels: list[str] | None = None
    language: str | None = None
    status: str | None = None
    body: str | None = None
