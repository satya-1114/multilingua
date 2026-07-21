"""Workflow asynchronous execution & scheduling package (Phase 8.3).

Public API:

* :data:`workflow_celery_app` — dedicated Celery application.
* :class:`WorkflowQueue` — queue abstraction (interface).
* :class:`CeleryWorkflowQueue` — Celery-backed queue.
* :class:`InMemoryWorkflowQueue` — deterministic, in-process queue used
  by tests and by :class:`WorkflowScheduler` when Celery is disabled.
* :func:`execute_workflow_task` — Celery task wrapping the runtime.
* :class:`WorkflowScheduler` — discovers enabled schedule triggers and
  enqueues them for execution.
* :mod:`cron` helpers — :func:`validate_cron`, :func:`next_run_at`.
"""
from __future__ import annotations

from .celery_app import WORKFLOW_QUEUES, workflow_celery_app
from .cron import (
    CronValidationError,
    next_run_at,
    parse_cron,
    validate_cron,
)
from .queue import (
    CeleryWorkflowQueue,
    EnqueueResult,
    InMemoryWorkflowQueue,
    WorkflowQueue,
    default_workflow_queue,
    set_default_workflow_queue,
)
from .scheduler import ScheduledRun, WorkflowScheduler
from .tasks import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF,
    RETRYABLE_EXCEPTIONS,
    execute_workflow_task,
    run_workflow_execution,
)

__all__ = [
    "CeleryWorkflowQueue",
    "CronValidationError",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_BACKOFF",
    "EnqueueResult",
    "InMemoryWorkflowQueue",
    "RETRYABLE_EXCEPTIONS",
    "ScheduledRun",
    "WORKFLOW_QUEUES",
    "WorkflowQueue",
    "WorkflowScheduler",
    "default_workflow_queue",
    "execute_workflow_task",
    "next_run_at",
    "parse_cron",
    "run_workflow_execution",
    "set_default_workflow_queue",
    "validate_cron",
    "workflow_celery_app",
]
