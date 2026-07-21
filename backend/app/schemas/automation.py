from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import IdentifiedDto


class AutomationDto(IdentifiedDto):
    name: str
    status: str
    version: int


class AutomationCreate(BaseModel):
    workspaceId: str
    name: str
    definition: dict = {}
