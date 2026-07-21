"""Pydantic schemas for public resources, QR metadata, and view tracking."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdentifiedDto


ResourceType = Literal[
    "disaster",
    "campaign",
    "volunteer_recruitment",
    "emergency_info",
    "donation",
    "organization",
    "other",
]
Visibility = Literal["public", "unlisted", "private", "expired", "disabled"]
QRStatus = Literal["pending", "active", "revoked", "expired"]
QRFormat = Literal["png", "svg", "pdf"]
DeviceType = Literal["mobile", "tablet", "desktop", "bot", "unknown"]


# -------- Public resource ---------------------------------------------------


class PublicResourceDto(IdentifiedDto):
    resourceType: ResourceType = Field(alias="resource_type")
    resourceId: uuid.UUID | None = Field(default=None, alias="resource_id")
    slug: str
    qrToken: str | None = Field(default=None, alias="qr_token")
    title: str
    description: str | None = None
    visibility: Visibility
    expiresAt: datetime | None = Field(default=None, alias="expires_at")
    organizationId: uuid.UUID | None = Field(default=None, alias="organization_id")
    createdByUserId: uuid.UUID | None = Field(default=None, alias="created_by_user_id")
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PublicResourceCreate(BaseModel):
    resourceType: ResourceType
    resourceId: uuid.UUID | None = None
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9\-]{0,118}[a-z0-9]$|^[a-z0-9]$")
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    visibility: Visibility = "public"
    expiresAt: datetime | None = None
    organizationId: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicResourceUpdate(BaseModel):
    slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        pattern=r"^[a-z0-9][a-z0-9\-]{0,118}[a-z0-9]$|^[a-z0-9]$",
    )
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    visibility: Visibility | None = None
    expiresAt: datetime | None = None
    organizationId: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None


class PublicResourceListQuery(BaseModel):
    search: str | None = None
    resourceType: ResourceType | None = None
    visibility: Visibility | None = None
    organizationId: uuid.UUID | None = None
    resourceId: uuid.UUID | None = None
    activeOnly: bool | None = None
    sortBy: str | None = None
    sortDir: Literal["asc", "desc"] | None = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)


# -------- QR code -----------------------------------------------------------


class QRCodeDto(IdentifiedDto):
    publicResourceId: uuid.UUID = Field(alias="public_resource_id")
    format: QRFormat
    version: int
    status: QRStatus
    generatedAt: datetime | None = Field(default=None, alias="generated_at")
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class QRCodeCreate(BaseModel):
    format: QRFormat = "png"
    version: int = Field(default=1, ge=1, le=40)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QRCodeUpdate(BaseModel):
    status: QRStatus | None = None
    metadata: dict[str, Any] | None = None


# -------- Public view -------------------------------------------------------


class PublicViewDto(IdentifiedDto):
    publicResourceId: uuid.UUID = Field(alias="public_resource_id")
    viewedAt: datetime = Field(alias="viewed_at")
    ipHash: str | None = Field(default=None, alias="ip_hash")
    userAgentHash: str | None = Field(default=None, alias="user_agent_hash")
    country: str | None = None
    deviceType: DeviceType | None = Field(default=None, alias="device_type")
    referrer: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PublicViewCreate(BaseModel):
    viewedAt: datetime | None = None
    ipHash: str | None = Field(default=None, max_length=64)
    userAgentHash: str | None = Field(default=None, max_length=64)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    deviceType: DeviceType | None = None
    referrer: str | None = Field(default=None, max_length=1024)
