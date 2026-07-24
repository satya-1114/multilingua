"""Workflow runtime executor (Phase 8.1).

Loads a workflow definition, walks its enabled actions in order, and
records step outcomes via the workflow service. Runtime concerns only:
no Celery, no scheduler, no HTTP.
"""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.constants.workflow import (
    STEP_STATUS_FAILED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_RUNNING,
)
from app.models.workflow import WorkflowAction, WorkflowDefinition
from app.repositories.workflow import (
    workflow_actions as _actions_repo,
    workflow_definitions as _defs_repo,
)
from app.runtime.context import WorkflowExecutionContext
from app.runtime.exceptions import (
    ActionExecutionError,
    InvalidWorkflowError,
    UnknownActionError,
    WorkflowRuntimeError,
)
from app.runtime.registry import ActionRegistry, default_registry
from app.runtime.result import ActionResult, ExecutionResult, _now
from app.runtime.monitoring.metrics import default_metrics
from app.observability.context import observed
from app.observability.metrics import observability_metrics
from app.observability.tracing import default_tracer
from app.services.workflow import (
    workflow_execution_service as _execution_service,
)


class WorkflowRuntimeExecutor:
    """Executes a workflow definition end-to-end."""

    def __init__(
        self,
        *,
        registry: ActionRegistry | None = None,
        execution_service=_execution_service,
        definitions_repo=_defs_repo,
        actions_repo=_actions_repo,
        logger: structlog.stdlib.BoundLogger | None = None,
    ) -> None:
        self.registry = registry or default_registry
        self.execution_service = execution_service
        self.definitions_repo = definitions_repo
        self.actions_repo = actions_repo
        self.logger = logger or structlog.get_logger("workflow.runtime")

    # -- validation ------------------------------------------------------- #

    def validate_workflow(
        self,
        workflow: WorkflowDefinition,
        actions: list[WorkflowAction],
    ) -> None:
        if not workflow.enabled:
            raise InvalidWorkflowError(
                "Workflow is disabled",
                details={"workflow_id": str(workflow.id)},
            )
        if not actions:
            raise InvalidWorkflowError(
                "Workflow has no actions",
                details={"workflow_id": str(workflow.id)},
            )
        for action in actions:
            if not self.registry.has(action.action_type):
                raise UnknownActionError(
                    f"No handler registered for action type {action.action_type!r}",
                    details={
                        "action_id": str(action.id),
                        "action_type": action.action_type,
                    },
                )

    # -- execution -------------------------------------------------------- #

    def execute(
        self,
        db: Session,
        workflow_id: uuid.UUID | str,
        *,
        trigger_event: str | None = None,
        trigger_payload: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        actor_id: uuid.UUID | str | None = None,
        stop_on_failure: bool = True,
        persist: bool = True,
    ) -> ExecutionResult:
        started = _now()
        wf = self.definitions_repo.get_definition(db, workflow_id)
        if wf is None:
            raise InvalidWorkflowError(
                "Workflow not found", details={"workflow_id": str(workflow_id)}
            )
        actions = self.actions_repo.ordered_actions(db, wf.id)
        enabled_actions = [a for a in actions if a.enabled]
        self.validate_workflow(wf, enabled_actions)

        execution = None
        execution_id: str | None = None
        if persist:
            execution = self.execution_service.start_execution(
                db,
                workflow_definition_id=wf.id,
                trigger_event=trigger_event,
                context=trigger_payload or {},
                metadata=metadata or {},
            )
            execution_id = str(execution.id)
        with observed(
            "workflow.execute",
            attributes={"workflow.id": str(wf.id), "action.count": len(enabled_actions)},
            workflow_id=str(wf.id),
            execution_id=execution_id,
            organization_id=str(getattr(wf, "organization_id", None) or "") or None,
        ) as _root_span:
            try:
                observability_metrics.record_execution()
            except Exception:  # pragma: no cover
                pass
            return self._run_actions(
                db=db,
                wf=wf,
                execution=execution,
                execution_id=execution_id,
                enabled_actions=enabled_actions,
                started=started,
                trigger_event=trigger_event,
                trigger_payload=trigger_payload,
                variables=variables,
                metadata=metadata,
                actor_id=actor_id,
                stop_on_failure=stop_on_failure,
                persist=persist,
                root_span=_root_span,
            )

    def _run_actions(
        self,
        *,
        db: Session,
        wf: WorkflowDefinition,
        execution,
        execution_id: str | None,
        enabled_actions: list[WorkflowAction],
        started,
        trigger_event,
        trigger_payload,
        variables,
        metadata,
        actor_id,
        stop_on_failure: bool,
        persist: bool,
        root_span=None,
    ) -> ExecutionResult:

        context = WorkflowExecutionContext(
            workflow=wf,
            execution=execution,
            organization_id=wf.organization_id,
            actor_id=actor_id,
            trigger_event=trigger_event,
            trigger_payload=trigger_payload or {},
            variables=variables or {},
            metadata=metadata or {},
            db=db,
            logger=self.logger.bind(
                workflow_id=str(wf.id), execution_id=execution_id
            ),
        )
        context.logger.info(
            "workflow.execution.start",
            trigger_event=trigger_event,
            action_count=len(enabled_actions),
        )

        step_results: list[ActionResult] = []
        overall_error: str | None = None
        overall_status = WORKFLOW_STATUS_RUNNING

        for action in enabled_actions:
            result = self._execute_action(db, context, action, persist=persist)
            step_results.append(result)
            if not result.success and stop_on_failure:
                overall_error = result.error
                overall_status = WORKFLOW_STATUS_FAILED
                break
        else:
            overall_status = WORKFLOW_STATUS_COMPLETED

        if not step_results:
            overall_status = WORKFLOW_STATUS_COMPLETED
        elif any(not r.success for r in step_results) and overall_status != WORKFLOW_STATUS_FAILED:
            overall_status = WORKFLOW_STATUS_FAILED
            overall_error = overall_error or next(
                (r.error for r in step_results if r.error), None
            )

        if persist and execution is not None:
            try:
                if overall_status == WORKFLOW_STATUS_COMPLETED:
                    self.execution_service.complete_execution(db, execution.id)
                else:
                    self.execution_service.fail_execution(
                        db, execution.id, reason=overall_error
                    )
            except Exception:  # pragma: no cover - defensive
                context.logger.exception("workflow.execution.finalize_failed")

        completed = _now()
        context.logger.info(
            "workflow.execution.finished",
            status=overall_status,
            duration=(completed - started).total_seconds(),
            steps=len(step_results),
        )
        try:
            default_metrics.record_execution(
                workflow_id=str(wf.id),
                status=overall_status,
                duration=(completed - started).total_seconds(),
            )
        except Exception:  # pragma: no cover - metrics must not break exec
            context.logger.exception("workflow.metrics.record_execution_failed")
        return ExecutionResult(
            workflow_id=str(wf.id),
            execution_id=execution_id,
            success=overall_status == WORKFLOW_STATUS_COMPLETED,
            status=overall_status,
            started_at=started,
            completed_at=completed,
            steps=step_results,
            error=overall_error,
        )

    # -- per-action ------------------------------------------------------- #

    def _execute_action(
        self,
        db: Session,
        context: WorkflowExecutionContext,
        action: WorkflowAction,
        *,
        persist: bool,
    ) -> ActionResult:
        step = None
        if persist and context.execution is not None:
            step = self.execution_service.create_step(
                db,
                execution_id=context.execution.id,
                action_id=action.id,
            )
            try:
                step = self.execution_service.transition_step(
                    db, step.id, "running"
                )
            except Exception:  # pragma: no cover - defensive
                context.logger.exception("workflow.step.start_failed")

        started = _now()
        log = context.bind_logger(
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            step_id=str(step.id) if step is not None else None,
            action_id=str(action.id),
            action_type=action.action_type,
        )
        try:
            handler = self.registry.get(action.action_type)
        except UnknownActionError as exc:
            completed = _now()
            log.error("workflow.step.unknown_handler", error=str(exc))
            result = ActionResult(
                action_type=action.action_type,
                success=False,
                status=STEP_STATUS_FAILED,
                started_at=started,
                completed_at=completed,
                error=str(exc),
                retryable=False,
                action_id=str(action.id),
            )
            self._finalize_step(db, step, result, persist=persist)
            return result

        config = dict(action.configuration_json or {})
        try:
            with default_tracer().start_span(
                f"workflow.action.{action.action_type}",
                attributes={
                    "action.id": str(action.id),
                    "action.type": action.action_type,
                    "handler": handler.name,
                    "workflow.id": context.workflow_id,
                    "execution.id": context.execution_id,
                },
            ) as _span:
                result = handler.execute(context, config)
            # Ensure the result carries traceability fields.
            result.action_id = str(action.id)
            result.handler = handler.name
        except ActionExecutionError as exc:
            completed = _now()
            log.error(
                "workflow.step.failed",
                handler=handler.name,
                duration=(completed - started).total_seconds(),
                error=exc.message,
                retryable=exc.retryable,
            )
            result = ActionResult(
                action_type=action.action_type,
                success=False,
                status=STEP_STATUS_FAILED,
                started_at=started,
                completed_at=completed,
                error=exc.message,
                retryable=exc.retryable,
                action_id=str(action.id),
                handler=handler.name,
            )
        except WorkflowRuntimeError as exc:
            completed = _now()
            log.error("workflow.step.runtime_error", error=exc.message)
            result = ActionResult(
                action_type=action.action_type,
                success=False,
                status=STEP_STATUS_FAILED,
                started_at=started,
                completed_at=completed,
                error=exc.message,
                retryable=False,
                action_id=str(action.id),
                handler=handler.name,
            )
        except Exception as exc:  # noqa: BLE001 - handler crash isolation
            completed = _now()
            log.exception("workflow.step.exception", handler=handler.name)
            result = ActionResult(
                action_type=action.action_type,
                success=False,
                status=STEP_STATUS_FAILED,
                started_at=started,
                completed_at=completed,
                error=str(exc),
                retryable=handler.supports_retry(),
                action_id=str(action.id),
                handler=handler.name,
            )
        else:
            log.info(
                "workflow.step.completed",
                handler=handler.name,
                duration=result.duration,
                status=result.status,
                success=result.success,
            )
        try:
            default_metrics.record_action(
                handler=result.handler or action.action_type,
                duration=result.duration,
                success=result.success,
            )
        except Exception:  # pragma: no cover
            context.logger.exception("workflow.metrics.record_action_failed")
        self._finalize_step(db, step, result, persist=persist)
        return result

    def _finalize_step(
        self,
        db: Session,
        step,
        result: ActionResult,
        *,
        persist: bool,
    ) -> None:
        if not persist or step is None:
            return
        try:
            target = result.status
            if target not in {"completed", "failed", "skipped"}:
                target = "completed" if result.success else "failed"
            self.execution_service.transition_step(
                db,
                step.id,
                target,
                output=result.output,
                error_message=result.error,
            )
        except Exception:  # pragma: no cover - defensive
            self.logger.exception("workflow.step.finalize_failed")


__all__ = ["WorkflowRuntimeExecutor"]
