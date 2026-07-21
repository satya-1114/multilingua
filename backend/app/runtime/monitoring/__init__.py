"""Runtime monitoring & observability (Phase 8.5).

Provides:

* :mod:`.metrics`      — in-process metric collector for the executor.
* :mod:`.history`      — retry history read model over persisted steps.
* :mod:`.health`       — structured health checks for runtime dependencies.
* :mod:`.statistics`   — aggregation service for executions & retries.

Nothing in this package requires external systems (Prometheus, OTEL,
etc.). It is intentionally minimal: the executor emits events into
``default_metrics`` and read APIs surface the aggregates.
"""
from __future__ import annotations

from .health import WorkflowRuntimeHealth, default_runtime_health
from .history import ExecutionRetryHistoryService, retry_history_service
from .metrics import MetricsCollector, MetricsSnapshot, default_metrics
from .statistics import WorkflowStatisticsService, workflow_statistics_service

__all__ = [
    "ExecutionRetryHistoryService",
    "MetricsCollector",
    "MetricsSnapshot",
    "WorkflowRuntimeHealth",
    "WorkflowStatisticsService",
    "default_metrics",
    "default_runtime_health",
    "retry_history_service",
    "workflow_statistics_service",
]