from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdentifiedDto


VolunteerStatus = Literal["available", "busy", "on_leave", "inactive"]
TaskPriority = Literal["low", "medium", "high", "urgent"]
TaskStatus = Literal[
    "pending", "accepted", "in_progress", "completed", "rejected", "cancelled"
]


# -------- Volunteer --------

class EmergencyContactDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str | None = None
    phone: str | None = None
    relation: str | None = None


class VolunteerDto(IdentifiedDto):
    userId: uuid.UUID
    organizationId: uuid.UUID | None = None
    languages: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    currentLocation: str | None = None
    availability: str | None = None
    status: VolunteerStatus = "available"
    emergencyContact: EmergencyContactDto | None = None


class VolunteerCreate(BaseModel):
    userId: uuid.UUID
    organizationId: uuid.UUID | None = None
    languages: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    currentLocation: str | None = Field(default=None, max_length=255)
    availability: str | None = Field(default=None, max_length=60)
    status: VolunteerStatus = "available"
    emergencyContact: EmergencyContactDto | None = None


class VolunteerUpdate(BaseModel):
    organizationId: uuid.UUID | None = None
    languages: list[str] | None = None
    skills: list[str] | None = None
    currentLocation: str | None = Field(default=None, max_length=255)
    availability: str | None = Field(default=None, max_length=60)
    status: VolunteerStatus | None = None
    emergencyContact: EmergencyContactDto | None = None


class VolunteerListQuery(BaseModel):
    search: str | None = None
    language: str | None = None
    skill: str | None = None
    location: str | None = None
    availability: str | None = None
    status: VolunteerStatus | None = None
    taskStatus: TaskStatus | None = None
    sortBy: str | None = None
    sortDir: Literal["asc", "desc"] | None = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)


# -------- Volunteer Task --------

class VolunteerTaskDto(IdentifiedDto):
    volunteerId: uuid.UUID
    campaignId: uuid.UUID | None = None
    title: str
    description: str | None = None
    priority: TaskPriority = "medium"
    status: TaskStatus = "pending"
    assignedAt: datetime | None = None
    dueAt: datetime | None = None
    completedAt: datetime | None = None
    createdByUserId: uuid.UUID | None = None


class VolunteerTaskCreate(BaseModel):
    volunteerId: uuid.UUID
    campaignId: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority = "medium"
    dueAt: datetime | None = None


class VolunteerTaskUpdate(BaseModel):
    campaignId: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: TaskPriority | None = None
    dueAt: datetime | None = None


class VolunteerTaskStatusUpdate(BaseModel):
    status: TaskStatus


class VolunteerTaskListQuery(BaseModel):
    volunteerId: uuid.UUID | None = None
    campaignId: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=200)
