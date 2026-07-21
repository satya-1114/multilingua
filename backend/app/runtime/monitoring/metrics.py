"""In-process metric collector for the workflow runtime (Phase 8.5).

The executor pushes lightweight, in-memory counters here at start/end
of each execution and after every action. No external systems are
used — the collector is meant to power the internal operational API
and dashboard. It is safe to call from multiple threads.

Design notes
------------
* All state lives on a single :class:`MetricsCollector` instance.
* ``default_metrics`` is imported by the executor and by API routes.
* Tests can construct a fresh :class:`MetricsCollector` to avoid
  cross-test bleed, or call ``reset()`` on the default.
* Durations are stored as floats in seconds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Aggregate:
    """Rolling sum/min/max/count for a single scalar series."""

    count: int = 0
    total: float = 0.0
    min: float | None = None
    max: float | None = None

    def record(self, value: float) -> None:
        value = max(float(value), 0.0)
        self.count += 1
        self.total += value
        self.min = value if self.min is None else min(self.min, value)
        self.max = value if self.max is None else max(self.max, value)

    @property
    def average(self) -> float:
        return self.total / self.count if self.count else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "total": round(self.total, 6),
            "average": round(self.average, 6),
            "min": self.min,
            "max": self.max,
        }


@dataclass
class MetricsSnapshot:
    """Read-only view of the collector's state at a point in time."""

    executions_total: int
    executions_by_status: dict[str, int]
    executions_by_workflow: dict[str, int]
    duration: dict[str, Any]
    handler_duration: dict[str, dict[str, Any]]
    queue_latency: dict[str, Any]
    retry_count: int
    action_success: int
    action_failure: int
    generated_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "executionsTotal": self.executions_total,
            "executionsByStatus": dict(self.executions_by_status),
            "executionsByWorkflow": dict(self.executions_by_workflow),
            "duration": self.duration,
            "handlerDuration": self.handler_duration,
            "queueLatency": self.queue_latency,
            "retryCount": self.retry_count,
            "actionSuccess": self.action_success,
            "actionFailure": self.action_failure,
            "generatedAt": self.generated_at.isoformat(),
        }


class MetricsCollector:
    """Thread-safe in-memory aggregation of runtime metrics."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._by_status: dict[str, int] = {}
        self._by_workflow: dict[str, int] = {}
        self._duration = _Aggregate()
        self._handlers: dict[str, _Aggregate] = {}
        self._queue_latency = _Aggregate()
        self._retry_count = 0
        self._action_success = 0
        self._action_failure = 0

    # -- recording -------------------------------------------------------- #

    def record_execution(
        self,
        *,
        workflow_id: str,
        status: str,
        duration: float,
    ) -> None:
        """Record a completed execution attempt."""
        with self._lock:
            self._by_status[status] = self._by_status.get(status, 0) + 1
            key = str(workflow_id)
            self._by_workflow[key] = self._by_workflow.get(key, 0) + 1
            self._duration.record(duration)

    def record_action(
        self,
        *,
        handler: str,
        duration: float,
        success: bool,
    ) -> None:
        """Record a single action execution outcome."""
        with self._lock:
            agg = self._handlers.setdefault(handler, _Aggregate())
            agg.record(duration)
            if success:
                self._action_success += 1
            else:
                self._action_failure += 1

    def record_queue_latency(self, seconds: float) -> None:
        with self._lock:
            self._queue_latency.record(seconds)

    def record_retry(self, *, workflow_id: str | None = None, count: int = 1) -> None:
        if count <= 0:
            return
        with self._lock:
            self._retry_count += int(count)

    # -- inspection ------------------------------------------------------- #

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            total = sum(self._by_status.values())
            handler_dict = {k: v.to_dict() for k, v in self._handlers.items()}
            return MetricsSnapshot(
                executions_total=total,
                executions_by_status=dict(self._by_status),
                executions_by_workflow=dict(self._by_workflow),
                duration=self._duration.to_dict(),
                handler_duration=handler_dict,
                queue_latency=self._queue_latency.to_dict(),
                retry_count=self._retry_count,
                action_success=self._action_success,
                action_failure=self._action_failure,
            )

    def success_rate(self) -> float:
        with self._lock:
            total = sum(self._by_status.values())
            if not total:
                return 0.0
            completed = self._by_status.get("completed", 0)
            return completed / total

    def failure_rate(self) -> float:
        with self._lock:
            total = sum(self._by_status.values())
            if not total:
                return 0.0
            failed = self._by_status.get("failed", 0)
            return failed / total

    def reset(self) -> None:
        with self._lock:
            self._by_status.clear()
            self._by_workflow.clear()
            self._duration = _Aggregate()
            self._handlers.clear()
            self._queue_latency = _Aggregate()
            self._retry_count = 0
            self._action_success = 0
            self._action_failure = 0


#: Module-level default collector used by the executor and API.
default_metrics = MetricsCollector()


__all__ = [
    "MetricsCollector",
    "MetricsSnapshot",
    "default_metrics",
]