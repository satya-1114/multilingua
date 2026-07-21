from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdentifiedDto


DisasterType = Literal[
    "flood",
    "fire",
    "cyclone",
    "earthquake",
    "landslide",
    "heatwave",
    "medical",
    "industrial",
    "public_safety",
    "other",
]
DisasterSeverity = Literal["low", "medium", "high", "critical"]
DisasterStatus = Literal[
    "reported", "verified", "active", "contained", "resolved", "closed"
]
AssignmentStatus = Literal[
    "assigned", "accepted", "in_progress", "completed", "cancelled"
]
AttachmentKind = Literal["image", "document", "evidence"]


# -------- Disaster ----------------------------------------------------------


class DisasterDto(IdentifiedDto):
    title: str
    description: str | None = None
    disasterType: DisasterType = Field(alias="disaster_type")
    severity: DisasterSeverity
    status: DisasterStatus
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = None
    postalCode: str | None = Field(default=None, alias="postal_code")
    startedAt: datetime | None = Field(default=None, alias="started_at")
    resolvedAt: datetime | None = Field(default=None, alias="resolved_at")
    organizationId: uuid.UUID | None = Field(default=None, alias="organization_id")
    createdByUserId: uuid.UUID | None = Field(default=None, alias="created_by_user_id")
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DisasterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    disasterType: DisasterType
    severity: DisasterSeverity = "medium"
    status: DisasterStatus = "reported"
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    postalCode: str | None = Field(default=None, max_length=20)
    startedAt: datetime | None = None
    organizationId: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DisasterUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    disasterType: DisasterType | None = None
    severity: DisasterSeverity | None = None
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    postalCode: str | None = Field(default=None, max_length=20)
    startedAt: datetime | None = None
    resolvedAt: datetime | None = None
    organizationId: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None


class DisasterStatusUpdate(BaseModel):
    status: DisasterStatus
    resolvedAt: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class DisasterListQuery(BaseModel):
    search: str | None = None
    disasterType: DisasterType | None = None
    severity: DisasterSeverity | None = None
    status: DisasterStatus | None = None
    organizationId: uuid.UUID | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = None
    startedFrom: datetime | None = None
    startedTo: datetime | None = None
    sortBy: str | None = None
    sortDir: Literal["asc", "desc"] | None = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)


# -------- Assignment --------------------------------------------------------


class DisasterAssignmentDto(IdentifiedDto):
    disasterId: uuid.UUID = Field(alias="disaster_id")
    volunteerId: uuid.UUID = Field(alias="volunteer_id")
    assignedByUserId: uuid.UUID | None = Field(default=None, alias="assigned_by_user_id")
    role: str | None = None
    status: AssignmentStatus
    assignedAt: datetime | None = Field(default=None, alias="assigned_at")
    completedAt: datetime | None = Field(default=None, alias="completed_at")
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DisasterAssignmentCreate(BaseModel):
    volunteerId: uuid.UUID
    role: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)


class DisasterAssignmentUpdate(BaseModel):
    role: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)


class DisasterAssignmentStatusUpdate(BaseModel):
    status: AssignmentStatus
    notes: str | None = Field(default=None, max_length=2000)


# -------- Attachment --------------------------------------------------------


class DisasterAttachmentDto(IdentifiedDto):
    disasterId: uuid.UUID = Field(alias="disaster_id")
    uploadedByUserId: uuid.UUID | None = Field(
        default=None, alias="uploaded_by_user_id"
    )
    kind: AttachmentKind
    fileName: str = Field(alias="file_name")
    fileUrl: str = Field(alias="file_url")
    contentType: str | None = Field(default=None, alias="content_type")
    sizeBytes: int | None = Field(default=None, alias="size_bytes")
    caption: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DisasterAttachmentCreate(BaseModel):
    kind: AttachmentKind = "image"
    fileName: str = Field(min_length=1, max_length=255)
    fileUrl: str = Field(min_length=1, max_length=1024)
    contentType: str | None = Field(default=None, max_length=120)
    sizeBytes: int | None = Field(default=None, ge=0)
    caption: str | None = Field(default=None, max_length=500)
