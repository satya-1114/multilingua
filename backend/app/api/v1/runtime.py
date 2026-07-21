"""Runtime monitoring API (Phase 8.5)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.models.user import User
from app.runtime.monitoring import (
    default_metrics,
    default_runtime_health,
    retry_history_service,
    workflow_statistics_service,
)
from app.observability import default_exporter, observability_metrics

router = APIRouter()


@router.get("/health", response_model=None, summary="Workflow runtime health")
def runtime_health(
    _: User = Depends(require_perm("workflow:manage")),
):
    return ok(default_runtime_health.check())


@router.get("/metrics", response_model=None, summary="Workflow runtime metrics snapshot")
def runtime_metrics(
    _: User = Depends(require_perm("workflow:manage")),
):
    return ok(default_metrics.snapshot().to_dict())


@router.get(
    "/statistics",
    response_model=None,
    summary="Workflow runtime aggregated statistics",
)
def runtime_statistics(
    since: datetime | None = Query(None),
    top_limit: int = Query(5, ge=1, le=50, alias="topLimit"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    overview = workflow_statistics_service.overview(db, since=since)
    top = workflow_statistics_service.top_workflows(db, limit=top_limit)
    fails = workflow_statistics_service.top_failures(db, limit=top_limit)
    return ok(
        {
            "overview": overview,
            "topWorkflows": top,
            "topFailures": fails,
            "metrics": default_metrics.snapshot().to_dict(),
        }
    )


@router.get(
    "/executions/{execution_id}/retries",
    response_model=None,
    summary="Retry history for an execution",
)
def execution_retries(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    return ok(retry_history_service.get_retry_history(db, execution_id))


@router.get(
    "/observability/metrics",
    response_model=None,
    summary="Extended observability metrics snapshot",
)
def observability_metrics_endpoint(
    _: User = Depends(require_perm("workflow:manage")),
):
    return ok(observability_metrics.snapshot())


@router.get(
    "/traces/{execution_id}",
    response_model=None,
    summary="Trace timeline for a workflow execution",
)
def execution_trace(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    key = str(execution_id)
    exporter = default_exporter()
    spans = [
        s for s in exporter.spans()
        if s.attributes.get("execution.id") == key
        or s.attributes.get("executionId") == key
    ]
    trace_id: str | None = spans[0].context.trace_id if spans else None
    if trace_id:
        spans = exporter.find_by_trace(trace_id)

    def _span_dict(s):
        d = s.to_dict()
        d["isRoot"] = s.context.parent_span_id is None
        return d

    spans_sorted = sorted(spans, key=lambda s: s.started_at)
    retry_history = retry_history_service.get_retry_history(db, execution_id)
    root = next((s for s in spans_sorted if s.context.parent_span_id is None), None)
    total_duration = (
        (max(s.ended_at or 0 for s in spans_sorted) - min(s.started_at for s in spans_sorted))
        if spans_sorted else 0.0
    )
    handlers: dict[str, dict] = {}
    for s in spans_sorted:
        handler = s.attributes.get("handler")
        if not handler:
            continue
        agg = handlers.setdefault(handler, {"count": 0, "totalDuration": 0.0})
        agg["count"] += 1
        agg["totalDuration"] += s.duration
    return ok(
        {
            "executionId": key,
            "traceId": trace_id,
            "rootSpan": _span_dict(root) if root else None,
            "spans": [_span_dict(s) for s in spans_sorted],
            "spanCount": len(spans_sorted),
            "totalDuration": total_duration,
            "handlerDurations": handlers,
            "retryTimeline": retry_history,
        }
    )


__all__ = ["router"]