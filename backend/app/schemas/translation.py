"""Pydantic schemas for the multilingual content platform (Phase 5.1).

Kept alongside the legacy AI-translation request/response DTOs — those
serve the ``/api/v1/translation`` free-text endpoint and are unchanged.
Everything below powers the per-entity translation platform.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdentifiedDto


# -- Legacy free-text translation DTOs (unchanged) ---------------------------


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    sourceLanguage: str | None = None
    targetLanguage: str = Field(min_length=2, max_length=10)
    workspaceId: str | None = None


class TranslationDto(IdentifiedDto):
    sourceLanguage: str
    targetLanguage: str
    sourceText: str
    translatedText: str
    quality: float


# -- Enum literals (mirror app.constants.translation) ------------------------

TranslationStatus = Literal["draft", "translated", "reviewed", "published"]
JobStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
SupportedEntityType = Literal[
    "disaster", "public_resource", "campaign", "organization"
]


# -- Entity translation ------------------------------------------------------


class EntityTranslationBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entityType: SupportedEntityType = Field(alias="entity_type")
    entityId: uuid.UUID = Field(alias="entity_id")
    locale: str = Field(min_length=2, max_length=20)
    fieldName: str = Field(alias="field_name", min_length=1, max_length=80)


class EntityTranslationCreate(EntityTranslationBase):
    translatedValue: str = Field(alias="translated_value", default="")
    status: TranslationStatus = "draft"
    sourceHash: str | None = Field(alias="source_hash", default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityTranslationUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    translatedValue: str | None = Field(alias="translated_value", default=None)
    status: TranslationStatus | None = None
    sourceHash: str | None = Field(alias="source_hash", default=None)
    reviewedByUserId: uuid.UUID | None = Field(
        alias="reviewed_by_user_id", default=None
    )
    metadata: dict[str, Any] | None = None


class EntityTranslationDto(IdentifiedDto):
    entityType: str = Field(alias="entity_type")
    entityId: uuid.UUID = Field(alias="entity_id")
    locale: str
    fieldName: str = Field(alias="field_name")
    translatedValue: str = Field(alias="translated_value")
    status: TranslationStatus
    sourceHash: str | None = Field(alias="source_hash", default=None)
    translatedByUserId: uuid.UUID | None = Field(
        alias="translated_by_user_id", default=None
    )
    reviewedByUserId: uuid.UUID | None = Field(
        alias="reviewed_by_user_id", default=None
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityTranslationListQuery(BaseModel):
    entityType: SupportedEntityType | None = None
    entityId: uuid.UUID | None = None
    locale: str | None = None
    status: TranslationStatus | None = None
    fieldName: str | None = None
    page: int = 1
    pageSize: int = 50


class EntityTranslationSearchQuery(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    entityType: SupportedEntityType | None = None
    locale: str | None = None
    status: TranslationStatus | None = None
    page: int = 1
    pageSize: int = 50


# -- Translation job ---------------------------------------------------------


class TranslationJobCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entityType: SupportedEntityType = Field(alias="entity_type")
    entityId: uuid.UUID = Field(alias="entity_id")
    sourceLocale: str = Field(alias="source_locale")
    targetLocale: str = Field(alias="target_locale")
    provider: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TranslationJobDto(IdentifiedDto):
    entityType: str = Field(alias="entity_type")
    entityId: uuid.UUID = Field(alias="entity_id")
    sourceLocale: str = Field(alias="source_locale")
    targetLocale: str = Field(alias="target_locale")
    status: JobStatus
    provider: str | None = None
    requestedByUserId: uuid.UUID | None = Field(
        alias="requested_by_user_id", default=None
    )
    requestedAt: datetime | None = Field(alias="requested_at", default=None)
    completedAt: datetime | None = Field(alias="completed_at", default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


# -- Translation locale ------------------------------------------------------


class TranslationLocaleCreate(BaseModel):
    locale: str = Field(min_length=2, max_length=20)
    displayName: str = Field(alias="display_name", min_length=1, max_length=120)
    nativeName: str | None = Field(alias="native_name", default=None)
    rtl: bool = False
    enabled: bool = True
    defaultLocale: bool = Field(alias="default_locale", default=False)
    sortOrder: int = Field(alias="sort_order", default=0)

    model_config = ConfigDict(populate_by_name=True)


class TranslationLocaleUpdate(BaseModel):
    displayName: str | None = Field(alias="display_name", default=None)
    nativeName: str | None = Field(alias="native_name", default=None)
    rtl: bool | None = None
    enabled: bool | None = None
    defaultLocale: bool | None = Field(alias="default_locale", default=None)
    sortOrder: int | None = Field(alias="sort_order", default=None)

    model_config = ConfigDict(populate_by_name=True)


class TranslationLocaleDto(IdentifiedDto):
    locale: str
    displayName: str = Field(alias="display_name")
    nativeName: str | None = Field(alias="native_name", default=None)
    rtl: bool
    enabled: bool
    defaultLocale: bool = Field(alias="default_locale")
    sortOrder: int = Field(alias="sort_order")
