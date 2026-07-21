"""Optional OpenTelemetry exporter adapter (Phase 9.3).

If ``opentelemetry-api`` is installed, forward spans to the configured
OTEL SDK. Otherwise the adapter is a no-op and the tracer keeps
functioning against the in-memory exporter.
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

from .spans import Span, SpanStatus
from .tracing import SpanExporter

log = get_logger(__name__)


def _try_import_otel() -> Any | None:
    try:  # pragma: no cover - optional dependency
        from opentelemetry import trace as otel_trace  # type: ignore
        return otel_trace
    except Exception:  # noqa: BLE001
        return None


class OpenTelemetryExporter(SpanExporter):
    """Adapter that mirrors internal :class:`Span` records into OTEL.

    On systems without ``opentelemetry`` installed, :attr:`enabled` is
    ``False`` and :meth:`export` becomes a structured-log fallback so
    operators can still see the trace stream.
    """

    name = "opentelemetry"

    def __init__(self, *, service_name: str = "app", tracer_provider: Any = None) -> None:
        self.service_name = service_name
        self._otel = _try_import_otel()
        self._tracer = None
        if self._otel is not None:
            try:  # pragma: no cover - integration path
                self._tracer = (
                    tracer_provider.get_tracer(service_name)
                    if tracer_provider is not None
                    else self._otel.get_tracer(service_name)
                )
            except Exception:  # noqa: BLE001
                self._tracer = None

    @property
    def enabled(self) -> bool:
        return self._tracer is not None

    def export(self, span: Span) -> None:
        if not self.enabled:
            # Fallback: emit a structured log line so downstream log-based
            # tracing (e.g. Cloudflare Logs) still receives the span.
            log.info(
                "observability.trace.span",
                span=span.name,
                trace_id=span.context.trace_id,
                span_id=span.context.span_id,
                parent_span_id=span.context.parent_span_id,
                duration=span.duration,
                status=span.status.value,
                attributes=span.attributes,
            )
            return
        # pragma: no cover - integration path
        try:
            otel_span = self._tracer.start_span(  # type: ignore[union-attr]
                span.name, start_time=int(span.started_at * 1e9),
            )
            for k, v in span.attributes.items():
                otel_span.set_attribute(k, v)
            for event in span.events:
                otel_span.add_event(
                    event.name,
                    attributes=event.attributes,
                    timestamp=int(event.timestamp * 1e9),
                )
            if span.status is SpanStatus.ERROR:
                from opentelemetry.trace import Status, StatusCode  # type: ignore

                otel_span.set_status(Status(StatusCode.ERROR, span.status_message or ""))
            end_time_ns = int((span.ended_at or span.started_at) * 1e9)
            otel_span.end(end_time=end_time_ns)
        except Exception:  # noqa: BLE001
            log.exception("observability.otel.export_failed")


__all__ = ["OpenTelemetryExporter"]
