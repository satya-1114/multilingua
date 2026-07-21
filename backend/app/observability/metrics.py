"""Extended observability metrics (Phase 9.3).

The Phase 8 :mod:`app.runtime.monitoring.metrics` collector tracks
execution outcomes. This module adds a small, orthogonal counter store
for HA / queue / handler telemetry that isn't tied to an execution row:

- leader transitions (elected / lost)
- lock acquisition / contention
- queue enqueue retries / failures
- webhook / runtime retries
- execution throughput (per-window rate)

The collector is thread-safe and lives as a module-level singleton.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import RLock
from typing import Any


@dataclass
class _Counter:
    value: int = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class _Rate:
    window_s: float = 60.0
    events: deque = field(default_factory=deque)

    def record(self, ts: float | None = None) -> None:
        now = ts if ts is not None else time.monotonic()
        self.events.append(now)
        self._trim(now)

    def _trim(self, now: float) -> None:
        while self.events and (now - self.events[0]) > self.window_s:
            self.events.popleft()

    def per_second(self, now: float | None = None) -> float:
        now = now if now is not None else time.monotonic()
        self._trim(now)
        if not self.events:
            return 0.0
        return len(self.events) / self.window_s

    def count(self) -> int:
        return len(self.events)


class ObservabilityMetrics:
    """Extra counters & rates that complement runtime metrics."""

    def __init__(self, *, throughput_window_s: float = 60.0) -> None:
        self._lock = RLock()
        self._counters: dict[str, _Counter] = {}
        self._throughput = _Rate(window_s=throughput_window_s)
        self._leader_elected = _Counter()
        self._leader_lost = _Counter()
        self._lock_acquired = _Counter()
        self._lock_contended = _Counter()
        self._queue_retries = _Counter()
        self._queue_failures = _Counter()
        self._webhook_retries = _Counter()
        self._runtime_retries = _Counter()
        # Phase 9.4 additions
        self._cache_hits = _Counter()
        self._cache_misses = _Counter()
        self._db_queries = _Counter()
        self._response_times: deque = deque(maxlen=1024)
        self._batch_enqueues = _Counter()
        self._queue_depth_sample: int = 0
        self._queue_capacity: int = 0

    # -- recording ------------------------------------------------------ #

    def record_leader_elected(self, node_id: str | None = None) -> None:
        with self._lock:
            self._leader_elected.inc()

    def record_leader_lost(self, node_id: str | None = None) -> None:
        with self._lock:
            self._leader_lost.inc()

    def record_lock_acquired(self, key: str | None = None) -> None:
        with self._lock:
            self._lock_acquired.inc()

    def record_lock_contended(self, key: str | None = None) -> None:
        with self._lock:
            self._lock_contended.inc()

    def record_queue_retry(self) -> None:
        with self._lock:
            self._queue_retries.inc()

    def record_queue_failure(self) -> None:
        with self._lock:
            self._queue_failures.inc()

    def record_webhook_retry(self) -> None:
        with self._lock:
            self._webhook_retries.inc()

    def record_runtime_retry(self) -> None:
        with self._lock:
            self._runtime_retries.inc()

    def record_execution(self) -> None:
        with self._lock:
            self._throughput.record()

    def counter(self, name: str, amount: int = 1) -> None:
        """Increment a free-form counter."""
        with self._lock:
            self._counters.setdefault(name, _Counter()).inc(amount)

    # -- Phase 9.4 recording ------------------------------------------- #

    def record_cache_hit(self, amount: int = 1) -> None:
        with self._lock:
            self._cache_hits.inc(amount)

    def record_cache_miss(self, amount: int = 1) -> None:
        with self._lock:
            self._cache_misses.inc(amount)

    def record_db_queries(self, amount: int = 1) -> None:
        with self._lock:
            self._db_queries.inc(amount)

    def record_response_time(self, seconds: float) -> None:
        if seconds < 0:
            return
        with self._lock:
            self._response_times.append(float(seconds))

    def record_batch_enqueue(self, size: int) -> None:
        with self._lock:
            self._batch_enqueues.inc(size)

    def record_queue_depth(self, depth: int, *, capacity: int = 0) -> None:
        with self._lock:
            self._queue_depth_sample = max(0, int(depth))
            self._queue_capacity = max(0, int(capacity))

    # -- inspection ----------------------------------------------------- #

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            total_cache = self._cache_hits.value + self._cache_misses.value
            hit_ratio = (
                round(self._cache_hits.value / total_cache, 6) if total_cache else 0.0
            )
            miss_ratio = (
                round(self._cache_misses.value / total_cache, 6)
                if total_cache
                else 0.0
            )
            times = list(self._response_times)
            avg_response = (
                round(sum(times) / len(times), 6) if times else 0.0
            )
            utilization = (
                round(
                    min(self._queue_depth_sample / self._queue_capacity, 1.0), 6
                )
                if self._queue_capacity
                else 0.0
            )
            return {
                "leaderElected": self._leader_elected.value,
                "leaderLost": self._leader_lost.value,
                "lockAcquired": self._lock_acquired.value,
                "lockContended": self._lock_contended.value,
                "queueRetries": self._queue_retries.value,
                "queueFailures": self._queue_failures.value,
                "webhookRetries": self._webhook_retries.value,
                "runtimeRetries": self._runtime_retries.value,
                "executionThroughput": {
                    "windowSeconds": self._throughput.window_s,
                    "count": self._throughput.count(),
                    "perSecond": round(self._throughput.per_second(), 6),
                },
                "cache": {
                    "hits": self._cache_hits.value,
                    "misses": self._cache_misses.value,
                    "hitRatio": hit_ratio,
                    "missRatio": miss_ratio,
                },
                "dbQueries": self._db_queries.value,
                "avgResponseTime": avg_response,
                "batchEnqueues": self._batch_enqueues.value,
                "queueUtilization": {
                    "depth": self._queue_depth_sample,
                    "capacity": self._queue_capacity,
                    "ratio": utilization,
                },
                "counters": {k: c.value for k, c in self._counters.items()},
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._throughput = _Rate(window_s=self._throughput.window_s)
            for c in (
                self._leader_elected, self._leader_lost, self._lock_acquired,
                self._lock_contended, self._queue_retries, self._queue_failures,
                self._webhook_retries, self._runtime_retries,
                self._cache_hits, self._cache_misses, self._db_queries,
                self._batch_enqueues,
            ):
                c.value = 0
            self._response_times.clear()
            self._queue_depth_sample = 0
            self._queue_capacity = 0


observability_metrics = ObservabilityMetrics()


__all__ = ["ObservabilityMetrics", "observability_metrics"]
