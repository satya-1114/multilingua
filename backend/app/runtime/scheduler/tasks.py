"""Workflow execution Celery task (Phase 8.3).

The task delegates to :func:`run_workflow_execution`, which is the
plain function unit tests import directly (no Celery machinery
needed). ``execute_workflow_task`` wraps it with retry policy and
structured logging.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from celery.exceptions import MaxRetriesExceededError, Retry

from app.core.logging import get_logger
from app.database.session import SessionLocal
from app.runtime.exceptions import (
    ActionExecutionError,
    InvalidWorkflowError,
    UnknownActionError,
)

from .celery_app import workflow_celery_app

log = get_logger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 30  # seconds, doubles with jitter per retry
DEFAULT_RETRY_JITTER = True

#: Exceptions that should NOT trigger a retry — deterministic user
#: errors (bad workflow, missing action handler).
NON_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    InvalidWorkflowError,
    UnknownActionError,
)

#: Exceptions that SHOULD trigger a retry — transient runtime issues.
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ActionExecutionError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def _to_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def run_workflow_execution(
    workflow_id: str,
    *,
    payload: dict[str, Any] | None = None,
    trigger_event: str | None = None,
    actor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    session_factory=SessionLocal,
    runtime_service=None,
) -> dict[str, Any]:
    """Load the runtime, execute the workflow, persist and return a
    serializable result dictionary.
    """
    from app.runtime.service import workflow_runtime_service as _default

    service = runtime_service or _default
    started = time.perf_counter()
    session = session_factory()
    try:
        result = service.execute_workflow(
            session,
            workflow_id,
            trigger_event=trigger_event or "queued",
            trigger_payload=dict(payload or {}),
            metadata=dict(metadata or {}),
            actor_id=_to_uuid(actor_id),
        )
        duration = time.perf_counter() - started
        payload_out = {
            "executionId": result.execution_id,
            "status": result.status,
            "success": result.success,
            "duration": duration,
            "workflowId": str(workflow_id),
        }
        log.info(
            "workflow.task.completed",
            workflow_id=str(workflow_id),
            execution_id=result.execution_id,
            status=result.status,
            duration=duration,
        )
        return payload_out
    finally:
        try:
            session.close()
        except Exception:  # pragma: no cover
            pass


def _compute_countdown(retries: int, base: int, *, jitter: bool = DEFAULT_RETRY_JITTER) -> float:
    """Exponential backoff with optional deterministic jitter."""
    delay = base * (2 ** max(retries, 0))
    if jitter:
        # Deterministic pseudo-jitter based on retry count so tests can assert.
        delay += (retries % 5)
    return float(delay)


@workflow_celery_app.task(
    name="workflow.execute",
    bind=True,
    max_retries=DEFAULT_MAX_RETRIES,
    acks_late=True,
    autoretry_for=(),
)
def execute_workflow_task(
    self,
    *,
    workflow_id: str,
    payload: dict[str, Any] | None = None,
    trigger_event: str | None = None,
    actor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Celery entry point for asynchronous workflow execution."""
    task_id = getattr(self.request, "id", None)
    retries = getattr(self.request, "retries", 0) or 0
    queue = getattr(self.request, "delivery_info", {}).get("routing_key")
    log.info(
        "workflow.task.started",
        task_id=task_id,
        workflow_id=str(workflow_id),
        queue=queue,
        retry_count=retries,
    )
    try:
        return run_workflow_execution(
            workflow_id,
            payload=payload,
            trigger_event=trigger_event,
            actor_id=actor_id,
            metadata=metadata,
        )
    except NON_RETRYABLE_EXCEPTIONS as exc:
        log.error(
            "workflow.task.non_retryable",
            task_id=task_id,
            workflow_id=str(workflow_id),
            error=str(exc),
        )
        raise
    except RETRYABLE_EXCEPTIONS as exc:
        countdown = _compute_countdown(retries, DEFAULT_RETRY_BACKOFF)
        log.warning(
            "workflow.task.retry",
            task_id=task_id,
            workflow_id=str(workflow_id),
            retry_count=retries + 1,
            countdown=countdown,
            error=str(exc),
        )
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            log.error(
                "workflow.task.exhausted",
                task_id=task_id,
                workflow_id=str(workflow_id),
                retry_count=retries,
                error=str(exc),
            )
            raise exc from None
    except Retry:  # pragma: no cover — bubble Celery's own signal
        raise
    except Exception as exc:  # noqa: BLE001 — treat unknown as retryable
        countdown = _compute_countdown(retries, DEFAULT_RETRY_BACKOFF)
        log.exception(
            "workflow.task.unexpected",
            task_id=task_id,
            workflow_id=str(workflow_id),
            retry_count=retries + 1,
        )
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            raise exc from None


__all__ = [
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_BACKOFF",
    "NON_RETRYABLE_EXCEPTIONS",
    "RETRYABLE_EXCEPTIONS",
    "_compute_countdown",
    "execute_workflow_task",
    "run_workflow_execution",
]
