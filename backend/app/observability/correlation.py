"""Request-scoped correlation IDs (Phase 9.3).

Every unit of work — HTTP request, workflow execution, Celery task,
event-bus dispatch — carries a small context object identifying the
originating request. Consumers grab ``current_correlation()`` at the
edges of the stack; new work spawned inside an existing context inherits
its identifiers.

Implemented on top of :class:`contextvars.ContextVar` so tasks and
async tasks propagate the state naturally.
"""
from __future__ import annotations

import contextvars
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator

import structlog


@dataclass(frozen=True)
class CorrelationContext:
    """Immutable snapshot of correlation identifiers."""

    correlation_id: str
    request_id: str
    workflow_id: str | None = None
    execution_id: str | None = None
    organization_id: str | None = None
    task_id: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None and v != {}}

    def to_headers(self) -> dict[str, str]:
        headers = {
            "X-Correlation-Id": self.correlation_id,
            "X-Request-Id": self.request_id,
        }
        if self.trace_id:
            headers["X-Trace-Id"] = self.trace_id
        if self.workflow_id:
            headers["X-Workflow-Id"] = self.workflow_id
        if self.execution_id:
            headers["X-Execution-Id"] = self.execution_id
        return headers

    def child(self, **overrides: Any) -> "CorrelationContext":
        base = {**asdict(self), **overrides}
        return CorrelationContext(**base)


_current: contextvars.ContextVar[CorrelationContext | None] = contextvars.ContextVar(
    "correlation_context", default=None
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def new_correlation_id() -> str:
    return _new_id("cor")


def new_request_id() -> str:
    return _new_id("req")


def new_trace_id() -> str:
    return uuid.uuid4().hex  # 32 hex chars, OTEL-compatible size


def new_span_id() -> str:
    return uuid.uuid4().hex[:16]  # 16 hex chars, OTEL-compatible size


def current_correlation() -> CorrelationContext | None:
    return _current.get()


def require_correlation() -> CorrelationContext:
    ctx = _current.get()
    if ctx is None:
        raise LookupError("no active correlation context")
    return ctx


def _bind_logging(ctx: CorrelationContext) -> None:
    """Inject IDs into structlog contextvars so every log line carries them."""
    fields = {
        "correlation_id": ctx.correlation_id,
        "request_id": ctx.request_id,
    }
    if ctx.workflow_id:
        fields["workflow_id"] = ctx.workflow_id
    if ctx.execution_id:
        fields["execution_id"] = ctx.execution_id
    if ctx.organization_id:
        fields["organization_id"] = ctx.organization_id
    if ctx.task_id:
        fields["task_id"] = ctx.task_id
    if ctx.trace_id:
        fields["trace_id"] = ctx.trace_id
    if ctx.span_id:
        fields["span_id"] = ctx.span_id
    structlog.contextvars.bind_contextvars(**fields)


def _unbind_logging(fields: list[str]) -> None:
    if fields:
        structlog.contextvars.unbind_contextvars(*fields)


@contextmanager
def use_correlation(ctx: CorrelationContext) -> Iterator[CorrelationContext]:
    """Bind ``ctx`` as the current correlation for the duration of the block."""
    previous = _current.get()
    token = _current.set(ctx)
    keys = list(ctx.to_dict().keys())
    _bind_logging(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)
        _unbind_logging(keys)
        if previous is not None:
            _bind_logging(previous)


def build_context(
    *,
    correlation_id: str | None = None,
    request_id: str | None = None,
    workflow_id: str | None = None,
    execution_id: str | None = None,
    organization_id: str | None = None,
    task_id: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> CorrelationContext:
    """Build a :class:`CorrelationContext` filling missing identifiers."""
    return CorrelationContext(
        correlation_id=correlation_id or new_correlation_id(),
        request_id=request_id or new_request_id(),
        workflow_id=workflow_id,
        execution_id=execution_id,
        organization_id=organization_id,
        task_id=task_id,
        trace_id=trace_id or new_trace_id(),
        span_id=span_id,
        parent_span_id=parent_span_id,
        attributes=attributes or {},
    )


def from_headers(headers: dict[str, str] | Any) -> CorrelationContext:
    """Rebuild a correlation context from HTTP-style headers.

    Missing identifiers are freshly generated.
    """
    get = headers.get if hasattr(headers, "get") else lambda k, d=None: d
    return build_context(
        correlation_id=get("X-Correlation-Id") or get("x-correlation-id"),
        request_id=get("X-Request-Id") or get("x-request-id"),
        trace_id=get("X-Trace-Id") or get("x-trace-id"),
        workflow_id=get("X-Workflow-Id") or get("x-workflow-id"),
        execution_id=get("X-Execution-Id") or get("x-execution-id"),
    )


__all__ = [
    "CorrelationContext",
    "build_context",
    "current_correlation",
    "from_headers",
    "new_correlation_id",
    "new_request_id",
    "new_span_id",
    "new_trace_id",
    "require_correlation",
    "use_correlation",
]
