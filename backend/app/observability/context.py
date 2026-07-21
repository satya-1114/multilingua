"""Helpers that fuse correlation + tracing into a single entry-point."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from .correlation import (
    CorrelationContext,
    build_context,
    current_correlation,
    use_correlation,
)
from .tracing import Tracer, default_tracer


@contextmanager
def observed(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
    tracer: Tracer | None = None,
    correlation: CorrelationContext | None = None,
    **fields: Any,
) -> Iterator[Any]:
    """Combine a correlation context and a root span in one block."""
    t = tracer or default_tracer()
    ctx = correlation or current_correlation()
    if ctx is None:
        ctx = build_context(**fields)
    elif fields:
        ctx = ctx.child(**fields)
    with use_correlation(ctx):
        with t.start_span(name, attributes=attributes) as span:
            span.set_attribute("correlation.id", ctx.correlation_id)
            span.set_attribute("request.id", ctx.request_id)
            if ctx.workflow_id:
                span.set_attribute("workflow.id", ctx.workflow_id)
            if ctx.execution_id:
                span.set_attribute("execution.id", ctx.execution_id)
            if ctx.organization_id:
                span.set_attribute("organization.id", ctx.organization_id)
            if ctx.task_id:
                span.set_attribute("task.id", ctx.task_id)
            yield span


__all__ = ["observed"]
