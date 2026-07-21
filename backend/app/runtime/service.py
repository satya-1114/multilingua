"""Runtime service facade (Phase 8.1).

Provides high-level entry points for callers that don't want to know
about the executor internals. Also owns the default handler
registration flow.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.workflow import (
    workflow_actions as _actions_repo,
    workflow_definitions as _defs_repo,
)
from app.runtime.action_handlers import (
    AnalyticsHandler,
    AuditHandler,
    EntityUpdateHandler,
    NotificationHandler,
    WebhookHandler,
)
from app.runtime.executor import WorkflowRuntimeExecutor
from app.runtime.exceptions import (
    InvalidWorkflowError,
    UnknownActionError,
)
from app.runtime.ha.idempotency import (
    IdempotencyStore,
    default_idempotency_store,
)
from app.runtime.registry import ActionRegistry, default_registry
from app.runtime.result import ActionResult, ExecutionResult, _now
from app.constants.workflow import WORKFLOW_STATUS_COMPLETED


EXECUTION_IDEMPOTENCY_TTL_S = 24 * 60 * 60  # 24h default replay window


DEFAULT_HANDLERS: tuple = (
    NotificationHandler,
    AuditHandler,
    AnalyticsHandler,
    WebhookHandler,
    EntityUpdateHandler,
)


class WorkflowRuntimeService:
    """Facade coordinating the executor + registry."""

    def __init__(
        self,
        *,
        registry: ActionRegistry | None = None,
        executor: WorkflowRuntimeExecutor | None = None,
        idempotency_store: IdempotencyStore | None = None,
    ) -> None:
        self.registry = registry or default_registry
        self.executor = executor or WorkflowRuntimeExecutor(registry=self.registry)
        self.idempotency_store = idempotency_store or default_idempotency_store()

    # -- registration ----------------------------------------------------- #

    def load_handlers(self, *, replace: bool = True) -> list[str]:
        """Register the built-in placeholder handlers."""
        loaded: list[str] = []
        for cls in DEFAULT_HANDLERS:
            handler = cls()
            self.registry.register(handler.action_type, handler, replace=replace)
            loaded.append(handler.action_type)
        return loaded

    # -- execution -------------------------------------------------------- #

    def execute_workflow(
        self,
        db: Session,
        workflow_id: uuid.UUID | str,
        **kwargs: Any,
    ) -> ExecutionResult:
        idem_key = _extract_idempotency_key(kwargs)
        if idem_key is not None:
            is_new, record = self.idempotency_store.remember(
                _namespace_key(workflow_id, idem_key),
                ttl_s=EXECUTION_IDEMPOTENCY_TTL_S,
            )
            if not is_new:
                return _duplicate_result(workflow_id, idem_key, record)
        return self.executor.execute(db, workflow_id, **kwargs)

    #: Synchronous alias for callers that want an explicit intent.
    def execute_sync(
        self,
        db: Session,
        workflow_id: uuid.UUID | str,
        **kwargs: Any,
    ) -> ExecutionResult:
        return self.execute_workflow(db, workflow_id, **kwargs)

    def enqueue_execution(
        self,
        workflow_id: uuid.UUID | str,
        *,
        payload: dict[str, Any] | None = None,
        trigger_event: str | None = None,
        actor_id: uuid.UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
        queue: str | None = None,
        run_at: Any = None,
    ):
        """Enqueue *workflow_id* on the configured workflow queue.

        Lazily imports the queue module to avoid a hard dependency on
        Celery when this facade is instantiated in tests.
        """
        from app.runtime.scheduler.queue import default_workflow_queue

        target = default_workflow_queue()
        if run_at is not None:
            return target.schedule(
                workflow_id,
                run_at=run_at,
                payload=payload,
                trigger_event=trigger_event,
                actor_id=actor_id,
                metadata=metadata,
                queue=queue,
            )
        return target.enqueue(
            workflow_id,
            payload=payload,
            trigger_event=trigger_event,
            actor_id=actor_id,
            metadata=metadata,
            queue=queue,
        )


    def execute_step(
        self,
        db: Session,
        *,
        workflow_id: uuid.UUID | str,
        action_id: uuid.UUID | str,
        trigger_payload: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        persist: bool = False,
    ) -> ActionResult:
        wf = _defs_repo.get_definition(db, workflow_id)
        if wf is None:
            raise InvalidWorkflowError(
                "Workflow not found", details={"workflow_id": str(workflow_id)}
            )
        action = _actions_repo.get_action(db, action_id)
        if action is None or action.workflow_definition_id != wf.id:
            raise InvalidWorkflowError(
                "Action does not belong to workflow",
                details={"workflow_id": str(workflow_id), "action_id": str(action_id)},
            )
        if not self.registry.has(action.action_type):
            raise UnknownActionError(
                f"No handler registered for {action.action_type!r}",
                details={"action_type": action.action_type},
            )
        from app.runtime.context import WorkflowExecutionContext

        context = WorkflowExecutionContext(
            workflow=wf,
            execution=None,
            organization_id=wf.organization_id,
            trigger_payload=trigger_payload or {},
            variables=variables or {},
            metadata=metadata or {},
            db=db,
        )
        return self.executor._execute_action(db, context, action, persist=persist)

    # -- diagnostics ------------------------------------------------------ #

    def validate_runtime(self) -> dict[str, Any]:
        return {
            "registeredActions": self.registry.registered_types(),
            "defaultHandlers": [cls.__name__ for cls in DEFAULT_HANDLERS],
            "checkedAt": _now().isoformat(),
        }


workflow_runtime_service = WorkflowRuntimeService()


def _extract_idempotency_key(kwargs: dict[str, Any]) -> str | None:
    md = kwargs.get("metadata") or {}
    if isinstance(md, dict):
        for k in ("idempotencyKey", "idempotency_key", "Idempotency-Key"):
            v = md.get(k)
            if isinstance(v, str) and v:
                return v
    return None


def _namespace_key(workflow_id, key: str) -> str:
    return f"workflow-exec:{workflow_id}:{key}"


def _duplicate_result(workflow_id, key: str, record) -> ExecutionResult:
    now = _now()
    return ExecutionResult(
        workflow_id=str(workflow_id),
        execution_id=None,
        success=True,
        status=WORKFLOW_STATUS_COMPLETED,
        started_at=now,
        completed_at=now,
        steps=[],
        error=None,
        metadata={
            "duplicateSuppressed": True,
            "idempotencyKey": key,
            "originalStoredAt": record.stored_at,
        },
    )


__all__ = ["WorkflowRuntimeService", "workflow_runtime_service", "DEFAULT_HANDLERS"]
