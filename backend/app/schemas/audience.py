from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import IdentifiedDto


class AudienceContactDto(IdentifiedDto):
    fullName: str
    email: EmailStr | None = None
    phone: str | None = None
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    status: str = "active"


class AudienceCreate(BaseModel):
    workspaceId: str
    fullName: str = Field(min_length=1, max_length=160)
    email: EmailStr | None = None
    phone: str | None = None
    language: str = "en"
    tags: list[str] = Field(default_factory=list)
    district: str | None = None
    state: str | None = None


class AudienceUpdate(BaseModel):
    fullName: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    status: str | None = None
