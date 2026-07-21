"""Observability primitives for the workflow runtime (Phase 9.3)."""
from __future__ import annotations

from .context import observed
from .correlation import (
    CorrelationContext,
    build_context,
    current_correlation,
    from_headers,
    new_correlation_id,
    new_request_id,
    new_span_id,
    new_trace_id,
    require_correlation,
    use_correlation,
)
from .exporters import OpenTelemetryExporter
from .metrics import ObservabilityMetrics, observability_metrics
from .spans import Span, SpanContext, SpanEvent, SpanStatus
from .tracing import (
    InMemorySpanExporter,
    NoopSpanExporter,
    SpanExporter,
    Tracer,
    current_span,
    default_exporter,
    default_tracer,
    reset_default_tracer,
    set_default_tracer,
)

__all__ = [
    "CorrelationContext",
    "InMemorySpanExporter",
    "NoopSpanExporter",
    "ObservabilityMetrics",
    "OpenTelemetryExporter",
    "Span",
    "SpanContext",
    "SpanEvent",
    "SpanExporter",
    "SpanStatus",
    "Tracer",
    "build_context",
    "current_correlation",
    "current_span",
    "default_exporter",
    "default_tracer",
    "from_headers",
    "new_correlation_id",
    "new_request_id",
    "new_span_id",
    "new_trace_id",
    "observability_metrics",
    "observed",
    "require_correlation",
    "reset_default_tracer",
    "set_default_tracer",
    "use_correlation",
]
