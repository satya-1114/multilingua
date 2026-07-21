from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import IdentifiedDto


class OrganizationDto(IdentifiedDto):
    name: str
    slug: str
    type: str
    status: str
    memberCount: int = 0


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=120)
    type: str = "Enterprise"
    website: str | None = None
    contactEmail: str | None = None
    region: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    status: str | None = None
    website: str | None = None
    contactEmail: str | None = None
    region: str | None = None
