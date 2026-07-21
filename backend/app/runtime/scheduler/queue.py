"""Workflow queue abstraction (Phase 8.3).

The rest of the runtime only knows the :class:`WorkflowQueue`
interface. Two implementations ship:

* :class:`CeleryWorkflowQueue` — production path (sends to Celery).
* :class:`InMemoryWorkflowQueue` — deterministic, test/CI friendly
  queue that stores enqueue requests in memory and can execute them
  synchronously.

The dispatcher and scheduler use ``default_workflow_queue`` so tests
can swap the implementation without touching call sites.
"""
from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.logging import get_logger

from .celery_app import WORKFLOW_QUEUE_MAIN, WORKFLOW_QUEUES, workflow_celery_app

log = get_logger(__name__)


class QueueUnavailable(RuntimeError):
    """Raised by :class:`ResilientWorkflowQueue` when all attempts fail."""


@dataclass(frozen=True)
class EnqueueResult:
    """Return value from :meth:`WorkflowQueue.enqueue`."""

    task_id: str
    queue: str
    workflow_id: str
    scheduled_for: datetime | None = None
    eta_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowQueue(abc.ABC):
    """Abstract queue interface for asynchronous workflow execution."""

    @abc.abstractmethod
    def enqueue(
        self,
        workflow_id: uuid.UUID | str,
        *,
        payload: dict[str, Any] | None = None,
        trigger_event: str | None = None,
        actor_id: uuid.UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
        queue: str | None = None,
    ) -> EnqueueResult:
        raise NotImplementedError

    @abc.abstractmethod
    def schedule(
        self,
        workflow_id: uuid.UUID | str,
        *,
        run_at: datetime,
        payload: dict[str, Any] | None = None,
        trigger_event: str | None = None,
        actor_id: uuid.UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
        queue: str | None = None,
    ) -> EnqueueResult:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Celery-backed implementation
# --------------------------------------------------------------------------- #


class CeleryWorkflowQueue(WorkflowQueue):
    """Send workflow tasks through the dedicated Celery app."""

    task_name = "workflow.execute"

    def __init__(self, *, celery_app=None, default_queue: str = WORKFLOW_QUEUE_MAIN):
        self.celery = celery_app or workflow_celery_app
        self.default_queue = default_queue

    def _resolve_queue(self, queue: str | None) -> str:
        target = queue or self.default_queue
        if target not in WORKFLOW_QUEUES:
            raise ValueError(f"unknown workflow queue {target!r}")
        return target

    def _build_kwargs(
        self,
        workflow_id: uuid.UUID | str,
        payload: dict[str, Any] | None,
        trigger_event: str | None,
        actor_id: uuid.UUID | str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "workflow_id": str(workflow_id),
            "payload": dict(payload or {}),
            "trigger_event": trigger_event,
            "actor_id": str(actor_id) if actor_id else None,
            "metadata": dict(metadata or {}),
        }

    def enqueue(
        self,
        workflow_id: uuid.UUID | str,
        *,
        payload: dict[str, Any] | None = None,
        trigger_event: str | None = None,
        actor_id: uuid.UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
        queue: str | None = None,
    ) -> EnqueueResult:
        target = self._resolve_queue(queue)
        kwargs = self._build_kwargs(
            workflow_id, payload, trigger_event, actor_id, metadata
        )
        async_result = self.celery.send_task(
            self.task_name, kwargs=kwargs, queue=target
        )
        log.info(
            "workflow.queue.enqueue",
            workflow_id=str(workflow_id),
            task_id=async_result.id,
            queue=target,
        )
        return EnqueueResult(
            task_id=async_result.id,
            queue=target,
            workflow_id=str(workflow_id),
            metadata=kwargs["metadata"],
        )

    def schedule(
        self,
        workflow_id: uuid.UUID | str,
        *,
        run_at: datetime,
        payload: dict[str, Any] | None = None,
        trigger_event: str | None = None,
        actor_id: uuid.UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
        queue: str | None = None,
    ) -> EnqueueResult:
        target = self._resolve_queue(queue)
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=timezone.utc)
        eta_seconds = max(
            (run_at - datetime.now(timezone.utc)).total_seconds(), 0.0
        )
        kwargs = self._build_kwargs(
            workflow_id, payload, trigger_event, actor_id, metadata
        )
        async_result = self.celery.send_task(
            self.task_name, kwargs=kwargs, queue=target, eta=run_at
        )
        log.info(
            "workflow.queue.schedule",
            workflow_id=str(workflow_id),
            task_id=async_result.id,
            queue=target,
            run_at=run_at.isoformat(),
        )
        return EnqueueResult(
            task_id=async_result.id,
            queue=target,
            workflow_id=str(workflow_id),
            scheduled_for=run_at,
            eta_seconds=eta_seconds,
            metadata=kwargs["metadata"],
        )


# --------------------------------------------------------------------------- #
# In-memory implementation
# --------------------------------------------------------------------------- #


@dataclass
class InMemoryTask:
    task_id: str
    workflow_id: str
    queue: str
    kwargs: dict[str, Any]
    enqueued_at: datetime
    run_at: datetime | None = None


class InMemoryWorkflowQueue(WorkflowQueue):
    """Test / development queue that records tasks in memory."""

    def __init__(self, *, default_queue: str = WORKFLOW_QUEUE_MAIN):
        self.default_queue = default_queue
        self._tasks: list[InMemoryTask] = []
        self._lock = RLock()
        self._enqueue_count = 0

    # -- WorkflowQueue --------------------------------------------------- #

    def _resolve_queue(self, queue: str | None) -> str:
        target = queue or self.default_queue
        if target not in WORKFLOW_QUEUES:
            raise ValueError(f"unknown workflow queue {target!r}")
        return target

    def _record(
        self,
        workflow_id: uuid.UUID | str,
        payload: dict[str, Any] | None,
        trigger_event: str | None,
        actor_id: uuid.UUID | str | None,
        metadata: dict[str, Any] | None,
        queue: str | None,
        run_at: datetime | None,
    ) -> EnqueueResult:
        target = self._resolve_queue(queue)
        task_id = uuid.uuid4().hex
        kwargs = {
            "workflow_id": str(workflow_id),
            "payload": dict(payload or {}),
            "trigger_event": trigger_event,
            "actor_id": str(actor_id) if actor_id else None,
            "metadata": dict(metadata or {}),
        }
        record = InMemoryTask(
            task_id=task_id,
            workflow_id=str(workflow_id),
            queue=target,
            kwargs=kwargs,
            enqueued_at=datetime.now(timezone.utc),
            run_at=run_at,
        )
        with self._lock:
            self._tasks.append(record)
            self._enqueue_count += 1
        eta_seconds: float | None = None
        if run_at is not None:
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=timezone.utc)
            eta_seconds = max(
                (run_at - datetime.now(timezone.utc)).total_seconds(), 0.0
            )
        return EnqueueResult(
            task_id=task_id,
            queue=target,
            workflow_id=str(workflow_id),
            scheduled_for=run_at,
            eta_seconds=eta_seconds,
            metadata=kwargs["metadata"],
        )

    def enqueue(
        self,
        workflow_id: uuid.UUID | str,
        *,
        payload: dict[str, Any] | None = None,
        trigger_event: str | None = None,
        actor_id: uuid.UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
        queue: str | None = None,
    ) -> EnqueueResult:
        return self._record(
            workflow_id, payload, trigger_event, actor_id, metadata, queue, None
        )

    def schedule(
        self,
        workflow_id: uuid.UUID | str,
        *,
        run_at: datetime,
        payload: dict[str, Any] | None = None,
        trigger_event: str | None = None,
        actor_id: uuid.UUID | str | None = None,
        metadata: dict[str, Any] | None = None,
        queue: str | None = None,
    ) -> EnqueueResult:
        return self._record(
            workflow_id, payload, trigger_event, actor_id, metadata, queue, run_at
        )

    # -- inspection helpers --------------------------------------------- #

    def tasks(self) -> list[InMemoryTask]:
        with self._lock:
            return list(self._tasks)

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()

    # -- Phase 9.4 batch / inspection ---------------------------------- #

    def enqueue_batch(
        self,
        items: list[dict[str, Any]],
        *,
        queue: str | None = None,
    ) -> list[EnqueueResult]:
        """Enqueue many tasks at once.

        Each ``item`` is a kwargs dict compatible with :meth:`enqueue`
        (must contain ``workflow_id``; ``payload``, ``metadata`` etc.
        are optional).
        """
        results: list[EnqueueResult] = []
        for item in items:
            if "workflow_id" not in item:
                raise ValueError("each batch item requires workflow_id")
            kwargs = dict(item)
            wf = kwargs.pop("workflow_id")
            kwargs.setdefault("queue", queue)
            results.append(self.enqueue(wf, **kwargs))
        return results

    def depth(self, *, queue: str | None = None) -> int:
        with self._lock:
            if queue is None:
                return len(self._tasks)
            return sum(1 for t in self._tasks if t.queue == queue)

    def depth_by_queue(self) -> dict[str, int]:
        with self._lock:
            out: dict[str, int] = {}
            for t in self._tasks:
                out[t.queue] = out.get(t.queue, 0) + 1
            return out

    def utilization(self, *, capacity: int) -> float:
        if capacity <= 0:
            return 0.0
        return round(min(self.depth() / capacity, 1.0), 6)

    def enqueue_count(self) -> int:
        with self._lock:
            return self._enqueue_count

    def pop_ready(self, *, now: datetime | None = None) -> list[InMemoryTask]:
        moment = now or datetime.now(timezone.utc)
        with self._lock:
            ready = [
                t for t in self._tasks
                if t.run_at is None or t.run_at <= moment
            ]
            self._tasks = [t for t in self._tasks if t not in ready]
        return ready

    def drain(self, *, db, runtime_service) -> list[dict[str, Any]]:
        """Execute every queued task synchronously; used by tests."""
        results: list[dict[str, Any]] = []
        for task in self.pop_ready():
            started = time.perf_counter()
            try:
                execution = runtime_service.execute_workflow(
                    db,
                    task.kwargs["workflow_id"],
                    trigger_event=task.kwargs.get("trigger_event") or "queued",
                    trigger_payload=task.kwargs.get("payload") or {},
                    metadata=task.kwargs.get("metadata") or {},
                    actor_id=_to_uuid(task.kwargs.get("actor_id")),
                )
                results.append(
                    {
                        "taskId": task.task_id,
                        "status": execution.status,
                        "success": execution.success,
                        "duration": time.perf_counter() - started,
                    }
                )
            except Exception as exc:  # noqa: BLE001 — test drain isolation
                results.append(
                    {
                        "taskId": task.task_id,
                        "status": "failed",
                        "success": False,
                        "error": str(exc),
                    }
                )
        return results


def _to_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Default queue (swappable)
# --------------------------------------------------------------------------- #


_default_queue: WorkflowQueue = InMemoryWorkflowQueue()


def default_workflow_queue() -> WorkflowQueue:
    return _default_queue


def set_default_workflow_queue(queue: WorkflowQueue) -> WorkflowQueue:
    global _default_queue
    previous = _default_queue
    _default_queue = queue
    return previous


# --------------------------------------------------------------------------- #
# Resilient wrapper (Phase 9.2)
# --------------------------------------------------------------------------- #


class ResilientWorkflowQueue(WorkflowQueue):
    """Wrap a :class:`WorkflowQueue` with retries and availability probes."""

    def __init__(
        self,
        inner: WorkflowQueue,
        *,
        max_attempts: int = 3,
        base_backoff_s: float = 0.05,
        max_backoff_s: float = 1.0,
        sleep=time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.inner = inner
        self.max_attempts = max_attempts
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self._sleep = sleep
        self._available = True
        self._last_error: str | None = None
        self._successes = 0
        self._failures = 0

    # -- diagnostics ---------------------------------------------------- #

    @property
    def available(self) -> bool:
        return self._available

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def stats(self) -> dict[str, Any]:
        return {
            "available": self._available,
            "successes": self._successes,
            "failures": self._failures,
            "lastError": self._last_error,
            "backend": type(self.inner).__name__,
        }

    def is_available(self) -> bool:
        # Cheap availability probe: for Celery, peek at broker connection;
        # for other backends we assume available. Never raises.
        try:
            probe = getattr(self.inner, "is_available", None)
            if callable(probe):
                self._available = bool(probe())
                return self._available
            self._available = True
            return True
        except Exception as exc:  # noqa: BLE001
            self._available = False
            self._last_error = str(exc)
            return False

    # -- retry engine --------------------------------------------------- #

    def _with_retry(self, op: str, fn) -> EnqueueResult:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = fn()
                self._available = True
                self._successes += 1
                if attempt > 1:
                    log.info(
                        "workflow.queue.retry_success",
                        op=op, attempt=attempt,
                    )
                return result
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._failures += 1
                self._last_error = str(exc)
                log.warning(
                    "workflow.queue.enqueue_retry",
                    op=op, attempt=attempt, error=str(exc),
                )
                try:
                    from app.observability.metrics import observability_metrics as _om
                    _om.record_queue_retry()
                except Exception:  # pragma: no cover
                    pass
                if attempt >= self.max_attempts:
                    break
                backoff = min(
                    self.max_backoff_s,
                    self.base_backoff_s * (2 ** (attempt - 1)),
                )
                self._sleep(backoff)
        self._available = False
        log.error(
            "workflow.queue.unavailable",
            op=op, attempts=self.max_attempts, error=self._last_error,
        )
        try:
            from app.observability.metrics import observability_metrics as _om
            _om.record_queue_failure()
        except Exception:  # pragma: no cover
            pass
        raise QueueUnavailable(
            f"queue.{op} failed after {self.max_attempts} attempts: {last_exc}"
        ) from last_exc

    # -- WorkflowQueue --------------------------------------------------- #

    def enqueue(self, workflow_id, **kwargs) -> EnqueueResult:
        return self._with_retry(
            "enqueue", lambda: self.inner.enqueue(workflow_id, **kwargs)
        )

    def schedule(self, workflow_id, *, run_at, **kwargs) -> EnqueueResult:
        return self._with_retry(
            "schedule",
            lambda: self.inner.schedule(workflow_id, run_at=run_at, **kwargs),
        )


__all__ = [
    "CeleryWorkflowQueue",
    "EnqueueResult",
    "InMemoryTask",
    "InMemoryWorkflowQueue",
    "QueueUnavailable",
    "ResilientWorkflowQueue",
    "WorkflowQueue",
    "default_workflow_queue",
    "set_default_workflow_queue",
]
