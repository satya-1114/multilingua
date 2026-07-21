from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import IdentifiedDto


class NotificationDto(IdentifiedDto):
    title: str
    message: str
    category: str
    priority: str
    read: bool = False


class NotificationCreate(BaseModel):
    userId: str
    title: str
    message: str
    category: str = "system"
    priority: str = "normal"
    href: str | None = None


class NotificationPreferenceDto(IdentifiedDto):
    channel: str
    enabled: bool
    quietHours: dict = {}
