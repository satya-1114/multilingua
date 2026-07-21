"""Trigger dispatcher (Phase 8.2).

Bridges the :class:`WorkflowEventBus` and the
:class:`~app.runtime.service.WorkflowRuntimeService`: when an event
lands on the bus, look up every enabled trigger whose event_name
matches, apply :func:`trigger_matches_event`, and execute each parent
workflow.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.workflow import WorkflowDefinition, WorkflowTrigger
from app.repositories.workflow import (
    workflow_definitions as _defs_repo,
    workflow_triggers as _triggers_repo,
)
from app.runtime.result import ExecutionResult
from app.runtime.service import (
    WorkflowRuntimeService,
    workflow_runtime_service,
)

from .event import WorkflowEvent
from .filters import trigger_matches_event

log = get_logger(__name__)


class WorkflowTriggerDispatcher:
    """Route events to matching workflow triggers."""

    def __init__(
        self,
        *,
        runtime_service: WorkflowRuntimeService | None = None,
        definitions_repo=_defs_repo,
        triggers_repo=_triggers_repo,
    ) -> None:
        self.runtime = runtime_service or workflow_runtime_service
        self.definitions_repo = definitions_repo
        self.triggers_repo = triggers_repo

    # -- discovery -------------------------------------------------------- #

    def find_matching_triggers(
        self, db: Session, event: WorkflowEvent
    ) -> list[WorkflowTrigger]:
        triggers, _ = self.triggers_repo.list_triggers(
            db, event_name=event.event_type, page=1, page_size=500
        )
        return [t for t in triggers if trigger_matches_event(t, event)]

    # -- dispatch --------------------------------------------------------- #

    def __call__(self, event: WorkflowEvent, context: dict[str, Any]) -> None:
        self.dispatch(event, context)

    def dispatch(
        self, event: WorkflowEvent, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        db: Session | None = context.get("db")
        if db is None:
            log.warning(
                "workflow.dispatch.no_session",
                event_type=event.event_type,
                correlation_id=event.correlation_id,
            )
            return []

        started = time.perf_counter()
        triggers = self.find_matching_triggers(db, event)
        results: list[dict[str, Any]] = []
        launched = 0
        for trigger in triggers:
            workflow: WorkflowDefinition | None = self.definitions_repo.get_definition(
                db, trigger.workflow_definition_id
            )
            if workflow is None or not workflow.enabled:
                log.info(
                    "workflow.dispatch.skip_disabled",
                    trigger_id=str(trigger.id),
                    workflow_id=str(trigger.workflow_definition_id),
                    correlation_id=event.correlation_id,
                )
                results.append(
                    {
                        "triggerId": str(trigger.id),
                        "workflowId": str(trigger.workflow_definition_id),
                        "launched": False,
                        "reason": "workflow_disabled",
                    }
                )
                continue
            try:
                execution: ExecutionResult = self.runtime.execute_workflow(
                    db,
                    workflow.id,
                    trigger_event=event.event_type,
                    trigger_payload=dict(event.payload or {}),
                    metadata={
                        "correlationId": event.correlation_id,
                        "eventTimestamp": event.timestamp.isoformat(),
                        "resourceType": event.resource_type,
                        "resourceId": event.resource_id,
                        "actorId": event.actor_id,
                        **({"dry_run": True} if context.get("dry_run") else {}),
                    },
                    actor_id=_coerce_uuid(event.actor_id),
                )
                launched += 1
                results.append(
                    {
                        "triggerId": str(trigger.id),
                        "workflowId": str(workflow.id),
                        "launched": True,
                        "executionId": execution.execution_id,
                        "status": execution.status,
                        "success": execution.success,
                    }
                )
                log.info(
                    "workflow.dispatch.executed",
                    trigger_id=str(trigger.id),
                    workflow_id=str(workflow.id),
                    correlation_id=event.correlation_id,
                    status=execution.status,
                )
            except Exception as exc:  # noqa: BLE001 — isolation
                results.append(
                    {
                        "triggerId": str(trigger.id),
                        "workflowId": str(workflow.id),
                        "launched": False,
                        "error": str(exc),
                    }
                )
                log.exception(
                    "workflow.dispatch.error",
                    trigger_id=str(trigger.id),
                    workflow_id=str(workflow.id),
                    correlation_id=event.correlation_id,
                )

        duration = time.perf_counter() - started
        log.info(
            "workflow.dispatch.summary",
            event_type=event.event_type,
            correlation_id=event.correlation_id,
            matched=len(triggers),
            launched=launched,
            duration=duration,
        )
        return results


def _coerce_uuid(value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


#: Module-level singleton wired to the default runtime service.
default_dispatcher = WorkflowTriggerDispatcher()


__all__ = ["WorkflowTriggerDispatcher", "default_dispatcher"]
