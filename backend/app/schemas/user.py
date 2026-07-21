from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import IdentifiedDto


class UserDto(IdentifiedDto):
    email: EmailStr
    fullName: str
    avatarUrl: str | None = None
    status: str = "active"
    roles: list[str] = Field(default_factory=list)


class UserCreate(BaseModel):
    email: EmailStr
    fullName: str
    password: str = Field(min_length=8)
    roles: list[str] = Field(default_factory=lambda: ["viewer"])


class UserUpdate(BaseModel):
    fullName: str | None = None
    avatarUrl: str | None = None
    status: str | None = None
    roles: list[str] | None = None
