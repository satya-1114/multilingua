from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import IdentifiedDto


class AudienceGroupDto(IdentifiedDto):
    workspaceId: str
    name: str
    description: str | None = None
    memberCount: int = 0


class AudienceGroupCreate(BaseModel):
    workspaceId: str
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)


class AudienceGroupUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
    )
    description: str | None = Field(
        default=None,
        max_length=500,
    )


class AddMembersRequest(BaseModel):
    audienceIds: list[str] = Field(
        min_length=1,
        max_length=1000,
    )