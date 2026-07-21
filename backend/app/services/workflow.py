"""Service layer for the Automation & Workflow Engine (Phase 7.2).

Business rules live here:

* Duplicate workflow name (per organization) detection.
* Unique/positive action ``sequence`` enforcement + reordering.
* Trigger / action / status literal validation.
* Immutable ``organization_id`` (definition) and
  ``workflow_definition_id`` (execution).
* Centralised execution / step transition maps.
* Retry semantics for failed steps.

The engine is intentionally transport-agnostic — it does not touch
FastAPI, Celery, notifications, webhooks, or analytics. Those wire
into events in later phases.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.constants.workflow import (
    ACTION_TYPES,
    STEP_STATUSES,
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
    STEP_STATUS_PENDING,
    STEP_STATUS_RUNNING,
    STEP_STATUS_SKIPPED,
    TRIGGER_TYPES,
    WORKFLOW_STATUSES,
    WORKFLOW_STATUS_CANCELLED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_PENDING,
    WORKFLOW_STATUS_RUNNING,
)
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.workflow import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
)
from app.repositories.workflow import (
    workflow_actions as _actions_repo,
    workflow_definitions as _defs_repo,
    workflow_execution_steps as _steps_repo,
    workflow_executions as _executions_repo,
    workflow_triggers as _triggers_repo,
)


# --------------------------------------------------------------------------- #
# Transition maps (single source of truth)
# --------------------------------------------------------------------------- #

EXECUTION_TRANSITIONS: dict[str, frozenset[str]] = {
    WORKFLOW_STATUS_PENDING: frozenset(
        {WORKFLOW_STATUS_RUNNING, WORKFLOW_STATUS_CANCELLED, WORKFLOW_STATUS_FAILED}
    ),
    WORKFLOW_STATUS_RUNNING: frozenset(
        {
            WORKFLOW_STATUS_COMPLETED,
            WORKFLOW_STATUS_FAILED,
            WORKFLOW_STATUS_CANCELLED,
        }
    ),
    WORKFLOW_STATUS_COMPLETED: frozenset(),
    WORKFLOW_STATUS_FAILED: frozenset(),
    WORKFLOW_STATUS_CANCELLED: frozenset(),
}

STEP_TRANSITIONS: dict[str, frozenset[str]] = {
    STEP_STATUS_PENDING: frozenset(
        {STEP_STATUS_RUNNING, STEP_STATUS_SKIPPED, STEP_STATUS_FAILED}
    ),
    STEP_STATUS_RUNNING: frozenset({STEP_STATUS_COMPLETED, STEP_STATUS_FAILED}),
    # Retry re-arms a failed step back to running.
    STEP_STATUS_FAILED: frozenset({STEP_STATUS_RUNNING}),
    STEP_STATUS_COMPLETED: frozenset(),
    STEP_STATUS_SKIPPED: frozenset(),
}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_execution_transition(current: str, target: str) -> None:
    if current == target:
        return
    allowed = EXECUTION_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise ValidationError(
            f"Illegal execution status transition: {current} -> {target}",
            details={"from": current, "to": target, "allowed": sorted(allowed)},
        )


def _assert_step_transition(current: str, target: str) -> None:
    if current == target:
        return
    allowed = STEP_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise ValidationError(
            f"Illegal step status transition: {current} -> {target}",
            details={"from": current, "to": target, "allowed": sorted(allowed)},
        )


def _validate_trigger_type(trigger_type: str) -> None:
    if trigger_type not in TRIGGER_TYPES:
        raise ValidationError(
            f"Invalid trigger type: {trigger_type!r}",
            details={"allowed": list(TRIGGER_TYPES)},
        )


def _validate_action_type(action_type: str) -> None:
    if action_type not in ACTION_TYPES:
        raise ValidationError(
            f"Invalid action type: {action_type!r}",
            details={"allowed": list(ACTION_TYPES)},
        )


def _validate_workflow_status(status: str) -> None:
    if status not in WORKFLOW_STATUSES:
        raise ValidationError(
            f"Invalid workflow status: {status!r}",
            details={"allowed": list(WORKFLOW_STATUSES)},
        )


def _validate_step_status(status: str) -> None:
    if status not in STEP_STATUSES:
        raise ValidationError(
            f"Invalid step status: {status!r}",
            details={"allowed": list(STEP_STATUSES)},
        )


# --------------------------------------------------------------------------- #
# WorkflowDefinitionService
# --------------------------------------------------------------------------- #


class WorkflowDefinitionService:
    """Business layer for workflow definitions."""

    def __init__(
        self,
        repo=_defs_repo,
        actions_repo=_actions_repo,
    ) -> None:
        self.repo = repo
        self.actions_repo = actions_repo

    def get_workflow(
        self, db: Session, workflow_id: uuid.UUID | str
    ) -> WorkflowDefinition:
        wf = self.repo.get_definition(db, workflow_id)
        if wf is None:
            raise NotFoundError("Workflow not found")
        return wf

    def create_workflow(
        self,
        db: Session,
        *,
        name: str,
        trigger_type: str,
        description: str | None = None,
        enabled: bool = True,
        organization_id: uuid.UUID | str | None = None,
        version: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowDefinition:
        if not name or not name.strip():
            raise ValidationError("Workflow name is required")
        _validate_trigger_type(trigger_type)
        if version < 1:
            raise ValidationError("version must be >= 1")

        if self.repo.find_by_name(
            db, name=name.strip(), organization_id=organization_id
        ) is not None:
            raise ConflictError(
                "Workflow with this name already exists in the organization",
                details={"name": name.strip()},
            )
        data = {
            "name": name.strip(),
            "description": description,
            "trigger_type": trigger_type,
            "enabled": enabled,
            "organization_id": organization_id,
            "version": version,
            "metadata_": metadata or {},
        }
        return self.repo.create_definition(db, data)

    def update_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID | str,
        *,
        name: str | None = None,
        description: str | None = None,
        trigger_type: str | None = None,
        enabled: bool | None = None,
        version: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowDefinition:
        wf = self.get_workflow(db, workflow_id)

        if trigger_type is not None:
            _validate_trigger_type(trigger_type)
        if version is not None and version < 1:
            raise ValidationError("version must be >= 1")

        if name is not None and name.strip() and name.strip() != wf.name:
            existing = self.repo.find_by_name(
                db, name=name.strip(), organization_id=wf.organization_id
            )
            if existing is not None and existing.id != wf.id:
                raise ConflictError(
                    "Workflow with this name already exists in the organization",
                    details={"name": name.strip()},
                )

        data: dict[str, Any] = {}
        if name is not None and name.strip():
            data["name"] = name.strip()
        if description is not None:
            data["description"] = description
        if trigger_type is not None:
            data["trigger_type"] = trigger_type
        if enabled is not None:
            data["enabled"] = enabled
        if version is not None:
            data["version"] = version
        if metadata is not None:
            data["metadata_"] = metadata

        # organization_id is immutable — silently ignored if attempted.
        return self.repo.update_definition(db, wf, data)

    def enable_workflow(
        self, db: Session, workflow_id: uuid.UUID | str
    ) -> WorkflowDefinition:
        return self.update_workflow(db, workflow_id, enabled=True)

    def disable_workflow(
        self, db: Session, workflow_id: uuid.UUID | str
    ) -> WorkflowDefinition:
        return self.update_workflow(db, workflow_id, enabled=False)

    def delete_workflow(self, db: Session, workflow_id: uuid.UUID | str) -> None:
        wf = self.get_workflow(db, workflow_id)
        self.repo.delete_definition(db, wf)

    def search_workflows(
        self,
        db: Session,
        *,
        query: str | None = None,
        page: int = 1,
        page_size: int = 50,
        trigger_type: str | None = None,
        enabled: bool | None = None,
        organization_id: uuid.UUID | str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[WorkflowDefinition], int]:
        if trigger_type is not None:
            _validate_trigger_type(trigger_type)
        if page < 1 or page_size < 1 or page_size > 500:
            raise ValidationError("Invalid pagination parameters")
        return self.repo.list_definitions(
            db,
            page=page,
            page_size=page_size,
            query=query,
            trigger_type=trigger_type,
            enabled=enabled,
            organization_id=organization_id,
            created_from=created_from,
            created_to=created_to,
        )


# --------------------------------------------------------------------------- #
# WorkflowActionService
# --------------------------------------------------------------------------- #


class WorkflowActionService:
    """Business layer for ordered workflow actions."""

    def __init__(
        self,
        repo=_actions_repo,
        definitions_repo=_defs_repo,
    ) -> None:
        self.repo = repo
        self.definitions_repo = definitions_repo

    def _assert_definition_exists(
        self, db: Session, workflow_definition_id: uuid.UUID | str
    ) -> WorkflowDefinition:
        wf = self.definitions_repo.get_definition(db, workflow_definition_id)
        if wf is None:
            raise NotFoundError("Workflow not found")
        return wf

    def create_action(
        self,
        db: Session,
        *,
        workflow_definition_id: uuid.UUID | str,
        sequence: int,
        action_type: str,
        configuration: dict[str, Any] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowAction:
        self._assert_definition_exists(db, workflow_definition_id)
        if sequence < 1:
            raise ValidationError("sequence must be a positive integer")
        _validate_action_type(action_type)
        if self.repo.find_by_sequence(
            db,
            workflow_definition_id=workflow_definition_id,
            sequence=sequence,
        ) is not None:
            raise ConflictError(
                "Action with this sequence already exists in the workflow",
                details={"sequence": sequence},
            )
        data = {
            "workflow_definition_id": workflow_definition_id,
            "sequence": sequence,
            "action_type": action_type,
            "configuration_json": configuration or {},
            "enabled": enabled,
            "metadata_": metadata or {},
        }
        return self.repo.create_action(db, data)

    def get_action(
        self, db: Session, action_id: uuid.UUID | str
    ) -> WorkflowAction:
        obj = self.repo.get_action(db, action_id)
        if obj is None:
            raise NotFoundError("Action not found")
        return obj

    def update_action(
        self,
        db: Session,
        action_id: uuid.UUID | str,
        *,
        sequence: int | None = None,
        action_type: str | None = None,
        configuration: dict[str, Any] | None = None,
        enabled: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowAction:
        obj = self.get_action(db, action_id)
        if action_type is not None:
            _validate_action_type(action_type)
        if sequence is not None:
            if sequence < 1:
                raise ValidationError("sequence must be a positive integer")
            if sequence != obj.sequence:
                clash = self.repo.find_by_sequence(
                    db,
                    workflow_definition_id=obj.workflow_definition_id,
                    sequence=sequence,
                )
                if clash is not None and clash.id != obj.id:
                    raise ConflictError(
                        "Action with this sequence already exists in the workflow",
                        details={"sequence": sequence},
                    )
        data: dict[str, Any] = {}
        if sequence is not None:
            data["sequence"] = sequence
        if action_type is not None:
            data["action_type"] = action_type
        if configuration is not None:
            data["configuration_json"] = configuration
        if enabled is not None:
            data["enabled"] = enabled
        if metadata is not None:
            data["metadata_"] = metadata
        # workflow_definition_id is immutable.
        return self.repo.update_action(db, obj, data)

    def delete_action(self, db: Session, action_id: uuid.UUID | str) -> None:
        obj = self.get_action(db, action_id)
        self.repo.delete_action(db, obj)

    def validate_action_sequence(
        self, db: Session, workflow_definition_id: uuid.UUID | str
    ) -> list[WorkflowAction]:
        """Ensure sequences are positive, contiguous from 1, and unique."""
        actions = self.repo.ordered_actions(db, workflow_definition_id)
        seen: set[int] = set()
        for idx, action in enumerate(actions, start=1):
            if action.sequence < 1:
                raise ValidationError(
                    "Action sequence must be positive",
                    details={"action_id": str(action.id)},
                )
            if action.sequence in seen:
                raise ConflictError(
                    "Duplicate action sequence detected",
                    details={"sequence": action.sequence},
                )
            seen.add(action.sequence)
            if action.sequence != idx:
                raise ValidationError(
                    "Action sequences must be contiguous starting from 1",
                    details={"expected": idx, "actual": action.sequence},
                )
        return actions

    def reorder_actions(
        self,
        db: Session,
        workflow_definition_id: uuid.UUID | str,
        ordered_action_ids: list[uuid.UUID | str],
    ) -> list[WorkflowAction]:
        """Assign sequences 1..N in the order provided.

        Uses a two-pass update (temporary negative sequences) to avoid
        violating the unique ``(workflow_definition_id, sequence)``
        constraint mid-flight.
        """
        self._assert_definition_exists(db, workflow_definition_id)
        current = self.repo.ordered_actions(db, workflow_definition_id)
        by_id = {str(a.id): a for a in current}

        if len(ordered_action_ids) != len(current):
            raise ValidationError(
                "Reorder list must contain every action of the workflow exactly once",
                details={"expected": len(current), "actual": len(ordered_action_ids)},
            )
        seen_ids: set[str] = set()
        for aid in ordered_action_ids:
            sid = str(aid)
            if sid not in by_id:
                raise ValidationError(
                    "Unknown action in reorder list",
                    details={"action_id": sid},
                )
            if sid in seen_ids:
                raise ValidationError(
                    "Duplicate action in reorder list",
                    details={"action_id": sid},
                )
            seen_ids.add(sid)

        # Pass 1 — park to negative sequences to free the target space.
        for i, action in enumerate(current, start=1):
            action.sequence = -i
        db.flush()

        # Pass 2 — assign 1..N in the requested order.
        for target, aid in enumerate(ordered_action_ids, start=1):
            by_id[str(aid)].sequence = target
        db.commit()

        return self.repo.ordered_actions(db, workflow_definition_id)


# --------------------------------------------------------------------------- #
# WorkflowExecutionService
# --------------------------------------------------------------------------- #


class WorkflowExecutionService:
    """Business layer for execution + step lifecycle."""

    def __init__(
        self,
        repo=_executions_repo,
        steps_repo=_steps_repo,
        definitions_repo=_defs_repo,
        actions_repo=_actions_repo,
    ) -> None:
        self.repo = repo
        self.steps_repo = steps_repo
        self.definitions_repo = definitions_repo
        self.actions_repo = actions_repo

    # -- execution --------------------------------------------------------- #

    def get_execution(
        self, db: Session, execution_id: uuid.UUID | str
    ) -> WorkflowExecution:
        obj = self.repo.get_execution(db, execution_id)
        if obj is None:
            raise NotFoundError("Execution not found")
        return obj

    def start_execution(
        self,
        db: Session,
        *,
        workflow_definition_id: uuid.UUID | str,
        trigger_event: str | None = None,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        wf = self.definitions_repo.get_definition(db, workflow_definition_id)
        if wf is None:
            raise NotFoundError("Workflow not found")
        if not wf.enabled:
            raise ValidationError(
                "Workflow is disabled and cannot be executed",
                details={"workflow_id": str(wf.id)},
            )
        data = {
            "workflow_definition_id": workflow_definition_id,
            "trigger_event": trigger_event,
            "status": WORKFLOW_STATUS_RUNNING,
            "started_at": _now(),
            "context_json": context or {},
            "metadata_": metadata or {},
        }
        return self.repo.create_execution(db, data)

    def _transition_execution(
        self,
        db: Session,
        execution_id: uuid.UUID | str,
        target: str,
        *,
        failure_reason: str | None = None,
    ) -> WorkflowExecution:
        _validate_workflow_status(target)
        exe = self.get_execution(db, execution_id)
        _assert_execution_transition(exe.status, target)
        data: dict[str, Any] = {"status": target}
        if target in {
            WORKFLOW_STATUS_COMPLETED,
            WORKFLOW_STATUS_FAILED,
            WORKFLOW_STATUS_CANCELLED,
        }:
            data["completed_at"] = _now()
        if failure_reason is not None:
            data["failure_reason"] = failure_reason
        return self.repo.update_execution(db, exe, data)

    def complete_execution(
        self, db: Session, execution_id: uuid.UUID | str
    ) -> WorkflowExecution:
        return self._transition_execution(db, execution_id, WORKFLOW_STATUS_COMPLETED)

    def fail_execution(
        self,
        db: Session,
        execution_id: uuid.UUID | str,
        *,
        reason: str | None = None,
    ) -> WorkflowExecution:
        return self._transition_execution(
            db, execution_id, WORKFLOW_STATUS_FAILED, failure_reason=reason
        )

    def cancel_execution(
        self,
        db: Session,
        execution_id: uuid.UUID | str,
        *,
        reason: str | None = None,
    ) -> WorkflowExecution:
        return self._transition_execution(
            db, execution_id, WORKFLOW_STATUS_CANCELLED, failure_reason=reason
        )

    def update_execution(
        self,
        db: Session,
        execution_id: uuid.UUID | str,
        *,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        exe = self.get_execution(db, execution_id)
        data: dict[str, Any] = {}
        if context is not None:
            data["context_json"] = context
        if metadata is not None:
            data["metadata_"] = metadata
        # workflow_definition_id and status handled by dedicated transitions.
        return self.repo.update_execution(db, exe, data)

    def delete_execution(
        self, db: Session, execution_id: uuid.UUID | str
    ) -> None:
        exe = self.get_execution(db, execution_id)
        self.repo.delete_execution(db, exe)

    def list_executions(
        self,
        db: Session,
        *,
        workflow_definition_id: uuid.UUID | str | None = None,
        status: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[WorkflowExecution], int]:
        if status is not None:
            _validate_workflow_status(status)
        if page < 1 or page_size < 1 or page_size > 500:
            raise ValidationError("Invalid pagination parameters")
        return self.repo.list_executions(
            db,
            workflow_definition_id=workflow_definition_id,
            status=status,
            started_from=started_from,
            started_to=started_to,
            page=page,
            page_size=page_size,
        )

    def execution_history(
        self,
        db: Session,
        workflow_definition_id: uuid.UUID | str,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[WorkflowExecution], int]:
        return self.list_executions(
            db,
            workflow_definition_id=workflow_definition_id,
            page=page,
            page_size=page_size,
        )

    # -- steps ------------------------------------------------------------- #

    def create_step(
        self,
        db: Session,
        *,
        execution_id: uuid.UUID | str,
        action_id: uuid.UUID | str,
        status: str = STEP_STATUS_PENDING,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowExecutionStep:
        _validate_step_status(status)
        exe = self.get_execution(db, execution_id)
        action = self.actions_repo.get_action(db, action_id)
        if action is None:
            raise NotFoundError("Action not found")
        if action.workflow_definition_id != exe.workflow_definition_id:
            raise ValidationError(
                "Action does not belong to the execution's workflow",
                details={
                    "action_id": str(action.id),
                    "execution_id": str(exe.id),
                },
            )
        data = {
            "workflow_execution_id": execution_id,
            "workflow_action_id": action_id,
            "status": status,
            "retry_count": 0,
            "metadata_": metadata or {},
        }
        return self.steps_repo.create_step(db, data)

    def get_step(
        self, db: Session, step_id: uuid.UUID | str
    ) -> WorkflowExecutionStep:
        obj = self.steps_repo.get_step(db, step_id)
        if obj is None:
            raise NotFoundError("Step not found")
        return obj

    def transition_step(
        self,
        db: Session,
        step_id: uuid.UUID | str,
        target: str,
        *,
        output: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> WorkflowExecutionStep:
        _validate_step_status(target)
        step = self.get_step(db, step_id)
        _assert_step_transition(step.status, target)
        data: dict[str, Any] = {"status": target}
        if target == STEP_STATUS_RUNNING and step.started_at is None:
            data["started_at"] = _now()
        if target in {STEP_STATUS_COMPLETED, STEP_STATUS_FAILED, STEP_STATUS_SKIPPED}:
            data["completed_at"] = _now()
        if output is not None:
            data["output_json"] = output
        if error_message is not None:
            data["error_message"] = error_message
        return self.steps_repo.update_step(db, step, data)

    def retry_step(
        self,
        db: Session,
        step_id: uuid.UUID | str,
        *,
        max_retries: int = 3,
    ) -> WorkflowExecutionStep:
        step = self.get_step(db, step_id)
        if step.status != STEP_STATUS_FAILED:
            raise ValidationError(
                "Only failed steps can be retried",
                details={"status": step.status},
            )
        if max_retries < 0:
            raise ValidationError("max_retries must be >= 0")
        if step.retry_count >= max_retries:
            raise ValidationError(
                "Retry limit reached",
                details={
                    "retry_count": step.retry_count,
                    "max_retries": max_retries,
                },
            )
        data = {
            "status": STEP_STATUS_RUNNING,
            "retry_count": step.retry_count + 1,
            "error_message": None,
            "started_at": _now(),
            "completed_at": None,
        }
        # Bypass CRUDBase.update's "skip None" behaviour for completed_at/error_message
        # by writing directly.
        for key, value in data.items():
            setattr(step, key, value)
        db.commit()
        db.refresh(step)
        return step

    def list_steps(
        self,
        db: Session,
        *,
        execution_id: uuid.UUID | str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[WorkflowExecutionStep], int]:
        if status is not None:
            _validate_step_status(status)
        if page < 1 or page_size < 1 or page_size > 500:
            raise ValidationError("Invalid pagination parameters")
        return self.steps_repo.list_steps(
            db,
            workflow_execution_id=execution_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    def delete_step(self, db: Session, step_id: uuid.UUID | str) -> None:
        obj = self.get_step(db, step_id)
        self.steps_repo.delete_step(db, obj)


# --------------------------------------------------------------------------- #
# Trigger service (thin — validation lives on the schema/service pair)
# --------------------------------------------------------------------------- #


class WorkflowTriggerService:
    def __init__(
        self,
        repo=_triggers_repo,
        definitions_repo=_defs_repo,
    ) -> None:
        self.repo = repo
        self.definitions_repo = definitions_repo

    def create_trigger(
        self,
        db: Session,
        *,
        workflow_definition_id: uuid.UUID | str,
        event_name: str,
        event_source: str | None = None,
        conditions: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        wf = self.definitions_repo.get_definition(db, workflow_definition_id)
        if wf is None:
            raise NotFoundError("Workflow not found")
        if not event_name or not event_name.strip():
            raise ValidationError("event_name is required")
        data = {
            "workflow_definition_id": workflow_definition_id,
            "event_name": event_name.strip(),
            "event_source": event_source,
            "conditions_json": conditions or {},
            "metadata_": metadata or {},
        }
        return self.repo.create_trigger(db, data)

    def get_trigger(self, db: Session, trigger_id: uuid.UUID | str):
        obj = self.repo.get_trigger(db, trigger_id)
        if obj is None:
            raise NotFoundError("Trigger not found")
        return obj

    def update_trigger(
        self,
        db: Session,
        trigger_id: uuid.UUID | str,
        *,
        event_name: str | None = None,
        event_source: str | None = None,
        conditions: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        obj = self.get_trigger(db, trigger_id)
        data: dict[str, Any] = {}
        if event_name is not None:
            if not event_name.strip():
                raise ValidationError("event_name cannot be empty")
            data["event_name"] = event_name.strip()
        if event_source is not None:
            data["event_source"] = event_source
        if conditions is not None:
            data["conditions_json"] = conditions
        if metadata is not None:
            data["metadata_"] = metadata
        return self.repo.update_trigger(db, obj, data)

    def delete_trigger(self, db: Session, trigger_id: uuid.UUID | str) -> None:
        obj = self.get_trigger(db, trigger_id)
        self.repo.delete_trigger(db, obj)

    def list_triggers(
        self,
        db: Session,
        *,
        workflow_definition_id: uuid.UUID | str | None = None,
        event_name: str | None = None,
        event_source: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ):
        return self.repo.list_triggers(
            db,
            workflow_definition_id=workflow_definition_id,
            event_name=event_name,
            event_source=event_source,
            page=page,
            page_size=page_size,
        )


# --------------------------------------------------------------------------- #
# Module-level service singletons
# --------------------------------------------------------------------------- #

workflow_definition_service = WorkflowDefinitionService()
workflow_action_service = WorkflowActionService()
workflow_execution_service = WorkflowExecutionService()
workflow_trigger_service = WorkflowTriggerService()


__all__ = [
    "EXECUTION_TRANSITIONS",
    "STEP_TRANSITIONS",
    "WorkflowDefinitionService",
    "WorkflowActionService",
    "WorkflowExecutionService",
    "WorkflowTriggerService",
    "workflow_definition_service",
    "workflow_action_service",
    "workflow_execution_service",
    "workflow_trigger_service",
]
