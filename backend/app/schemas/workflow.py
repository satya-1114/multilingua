"""Pydantic schemas for the Automation & Workflow Engine (Phase 7.1)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import IdentifiedDto


TriggerType = Literal["event", "schedule", "manual"]
WorkflowStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
StepStatus = Literal["pending", "running", "completed", "failed", "skipped"]
ActionType = Literal[
    "notification",
    "audit",
    "analytics",
    "webhook",
    "email",
    "sms",
    "update_entity",
    "custom",
]


# --------------------------------------------------------------------------- #
# WorkflowDefinition
# --------------------------------------------------------------------------- #


class WorkflowDefinitionBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    triggerType: TriggerType = Field(alias="trigger_type")
    enabled: bool = True
    organizationId: uuid.UUID | None = Field(alias="organization_id", default=None)
    version: int = Field(default=1, ge=1)


class WorkflowDefinitionCreate(WorkflowDefinitionBase):
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinitionUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    triggerType: TriggerType | None = Field(alias="trigger_type", default=None)
    enabled: bool | None = None
    version: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] | None = None


class WorkflowDefinitionDto(IdentifiedDto):
    name: str
    description: str | None = None
    triggerType: TriggerType = Field(alias="trigger_type")
    enabled: bool
    organizationId: uuid.UUID | None = Field(alias="organization_id", default=None)
    version: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinitionListQuery(BaseModel):
    triggerType: TriggerType | None = None
    enabled: bool | None = None
    organizationId: uuid.UUID | None = None
    page: int = 1
    pageSize: int = 50


class WorkflowSearchQuery(BaseModel):
    q: str | None = None
    triggerType: TriggerType | None = None
    status: WorkflowStatus | None = None
    page: int = 1
    pageSize: int = 50


# --------------------------------------------------------------------------- #
# WorkflowTrigger
# --------------------------------------------------------------------------- #


class WorkflowTriggerBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workflowDefinitionId: uuid.UUID = Field(alias="workflow_definition_id")
    eventName: str = Field(alias="event_name", min_length=1, max_length=120)
    eventSource: str | None = Field(alias="event_source", default=None, max_length=120)
    conditionsJson: dict[str, Any] = Field(
        alias="conditions_json", default_factory=dict
    )


class WorkflowTriggerCreate(WorkflowTriggerBase):
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowTriggerUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    eventName: str | None = Field(alias="event_name", default=None, max_length=120)
    eventSource: str | None = Field(alias="event_source", default=None, max_length=120)
    conditionsJson: dict[str, Any] | None = Field(alias="conditions_json", default=None)
    metadata: dict[str, Any] | None = None


class WorkflowTriggerDto(IdentifiedDto):
    workflowDefinitionId: uuid.UUID = Field(alias="workflow_definition_id")
    eventName: str = Field(alias="event_name")
    eventSource: str | None = Field(alias="event_source", default=None)
    conditionsJson: dict[str, Any] = Field(alias="conditions_json", default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# WorkflowAction
# --------------------------------------------------------------------------- #


class WorkflowActionBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workflowDefinitionId: uuid.UUID = Field(alias="workflow_definition_id")
    sequence: int = Field(ge=1)
    actionType: ActionType = Field(alias="action_type")
    configurationJson: dict[str, Any] = Field(
        alias="configuration_json", default_factory=dict
    )
    enabled: bool = True


class WorkflowActionCreate(WorkflowActionBase):
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowActionUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sequence: int | None = Field(default=None, ge=1)
    actionType: ActionType | None = Field(alias="action_type", default=None)
    configurationJson: dict[str, Any] | None = Field(
        alias="configuration_json", default=None
    )
    enabled: bool | None = None
    metadata: dict[str, Any] | None = None


class WorkflowActionDto(IdentifiedDto):
    workflowDefinitionId: uuid.UUID = Field(alias="workflow_definition_id")
    sequence: int
    actionType: ActionType = Field(alias="action_type")
    configurationJson: dict[str, Any] = Field(
        alias="configuration_json", default_factory=dict
    )
    enabled: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# WorkflowExecution
# --------------------------------------------------------------------------- #


class WorkflowExecutionBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workflowDefinitionId: uuid.UUID = Field(alias="workflow_definition_id")
    triggerEvent: str | None = Field(alias="trigger_event", default=None, max_length=120)
    status: WorkflowStatus = "pending"
    contextJson: dict[str, Any] = Field(alias="context_json", default_factory=dict)

    @model_validator(mode="after")
    def _validate_period(self):
        return self


class WorkflowExecutionCreate(WorkflowExecutionBase):
    startedAt: datetime | None = Field(alias="started_at", default=None)
    completedAt: datetime | None = Field(alias="completed_at", default=None)
    failureReason: str | None = Field(alias="failure_reason", default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_completion(self):
        if (
            self.startedAt is not None
            and self.completedAt is not None
            and self.completedAt < self.startedAt
        ):
            raise ValueError("completed_at must be >= started_at")
        return self


class WorkflowExecutionUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: WorkflowStatus | None = None
    startedAt: datetime | None = Field(alias="started_at", default=None)
    completedAt: datetime | None = Field(alias="completed_at", default=None)
    failureReason: str | None = Field(alias="failure_reason", default=None)
    contextJson: dict[str, Any] | None = Field(alias="context_json", default=None)
    metadata: dict[str, Any] | None = None


class WorkflowExecutionDto(IdentifiedDto):
    workflowDefinitionId: uuid.UUID = Field(alias="workflow_definition_id")
    triggerEvent: str | None = Field(alias="trigger_event", default=None)
    status: WorkflowStatus
    startedAt: datetime | None = Field(alias="started_at", default=None)
    completedAt: datetime | None = Field(alias="completed_at", default=None)
    failureReason: str | None = Field(alias="failure_reason", default=None)
    contextJson: dict[str, Any] = Field(alias="context_json", default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionListQuery(BaseModel):
    workflowDefinitionId: uuid.UUID | None = None
    status: WorkflowStatus | None = None
    startedFrom: datetime | None = None
    startedTo: datetime | None = None
    page: int = 1
    pageSize: int = 50


# --------------------------------------------------------------------------- #
# WorkflowExecutionStep
# --------------------------------------------------------------------------- #


class WorkflowExecutionStepBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    workflowExecutionId: uuid.UUID = Field(alias="workflow_execution_id")
    workflowActionId: uuid.UUID = Field(alias="workflow_action_id")
    status: StepStatus = "pending"
    retryCount: int = Field(alias="retry_count", default=0, ge=0)


class WorkflowExecutionStepCreate(WorkflowExecutionStepBase):
    startedAt: datetime | None = Field(alias="started_at", default=None)
    completedAt: datetime | None = Field(alias="completed_at", default=None)
    outputJson: dict[str, Any] = Field(alias="output_json", default_factory=dict)
    errorMessage: str | None = Field(alias="error_message", default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecutionStepUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: StepStatus | None = None
    startedAt: datetime | None = Field(alias="started_at", default=None)
    completedAt: datetime | None = Field(alias="completed_at", default=None)
    retryCount: int | None = Field(alias="retry_count", default=None, ge=0)
    outputJson: dict[str, Any] | None = Field(alias="output_json", default=None)
    errorMessage: str | None = Field(alias="error_message", default=None)
    metadata: dict[str, Any] | None = None


class WorkflowExecutionStepDto(IdentifiedDto):
    workflowExecutionId: uuid.UUID = Field(alias="workflow_execution_id")
    workflowActionId: uuid.UUID = Field(alias="workflow_action_id")
    status: StepStatus
    startedAt: datetime | None = Field(alias="started_at", default=None)
    completedAt: datetime | None = Field(alias="completed_at", default=None)
    retryCount: int = Field(alias="retry_count")
    outputJson: dict[str, Any] = Field(alias="output_json", default_factory=dict)
    errorMessage: str | None = Field(alias="error_message", default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
