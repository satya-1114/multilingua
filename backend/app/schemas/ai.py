from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import IdentifiedDto


class AiGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    mode: str = "generate"
    tone: str | None = None
    language: str = "en"
    workspaceId: str | None = None
    context: dict = {}


class AiGenerationDto(IdentifiedDto):
    prompt: str
    model: str
    tokens: int
    content: str


class PromptDto(IdentifiedDto):
    name: str
    category: str
    body: str
    variables: list[dict] = []
