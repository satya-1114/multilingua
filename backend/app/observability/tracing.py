"""Tracer abstraction (Phase 9.3).

Provides an OpenTelemetry-compatible surface (`start_span`, child spans,
attributes, events, status) without requiring any external exporter.
All spans finished by the tracer are pushed to registered
:class:`SpanExporter` implementations. Callers can install the optional
OTEL exporter to forward to a real backend.
"""
from __future__ import annotations

import contextvars
import time
from contextlib import contextmanager
from threading import RLock
from typing import Any, Callable, Iterator

from app.core.logging import get_logger

from .correlation import (
    current_correlation,
    new_span_id,
    new_trace_id,
    use_correlation,
)
from .spans import Span, SpanContext, SpanStatus

log = get_logger(__name__)


class SpanExporter:
    """Abstract exporter — receives completed spans."""

    name: str = "abstract"

    def export(self, span: Span) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def shutdown(self) -> None:  # pragma: no cover - default noop
        pass


class InMemorySpanExporter(SpanExporter):
    """Keep the last N spans in memory. Useful for tests + the trace API."""

    name = "in_memory"

    def __init__(self, *, capacity: int = 1000) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._lock = RLock()
        self._spans: list[Span] = []

    def export(self, span: Span) -> None:
        with self._lock:
            self._spans.append(span)
            if len(self._spans) > self.capacity:
                # drop oldest
                del self._spans[: len(self._spans) - self.capacity]

    def spans(self) -> list[Span]:
        with self._lock:
            return list(self._spans)

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()

    def find_by_trace(self, trace_id: str) -> list[Span]:
        with self._lock:
            return [s for s in self._spans if s.context.trace_id == trace_id]

    def find_by_attribute(self, key: str, value: Any) -> list[Span]:
        with self._lock:
            return [s for s in self._spans if s.attributes.get(key) == value]


class NoopSpanExporter(SpanExporter):
    name = "noop"

    def export(self, span: Span) -> None:  # pragma: no cover - intentional
        return


_current_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "current_span", default=None
)


def current_span() -> Span | None:
    return _current_span.get()


class Tracer:
    """Owns exporters + span factory."""

    def __init__(
        self,
        *,
        service_name: str = "app",
        exporters: list[SpanExporter] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.service_name = service_name
        self.exporters: list[SpanExporter] = list(exporters or [])
        self.clock = clock

    # -- exporter management ------------------------------------------- #

    def add_exporter(self, exporter: SpanExporter) -> None:
        self.exporters.append(exporter)

    def remove_exporter(self, exporter: SpanExporter) -> bool:
        try:
            self.exporters.remove(exporter)
            return True
        except ValueError:
            return False

    def clear_exporters(self) -> None:
        self.exporters.clear()

    # -- span lifecycle ------------------------------------------------- #

    def _resolve_parent(self) -> tuple[str, str | None]:
        parent = _current_span.get()
        if parent is not None:
            return parent.context.trace_id, parent.context.span_id
        cor = current_correlation()
        if cor is not None:
            return cor.trace_id or new_trace_id(), cor.span_id
        return new_trace_id(), None

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        parent: Span | None = None,
    ) -> Iterator[Span]:
        if parent is not None:
            trace_id = parent.context.trace_id
            parent_span_id = parent.context.span_id
        else:
            trace_id, parent_span_id = self._resolve_parent()
        span = Span(
            name=name,
            context=SpanContext(
                trace_id=trace_id,
                span_id=new_span_id(),
                parent_span_id=parent_span_id,
            ),
            started_at=self.clock(),
            attributes={
                "service.name": self.service_name,
                **(attributes or {}),
            },
        )
        token = _current_span.set(span)
        # keep correlation trace/span in sync
        cor = current_correlation()
        if cor is not None:
            new_cor = cor.child(
                trace_id=trace_id,
                span_id=span.context.span_id,
                parent_span_id=parent_span_id,
            )
            cm = use_correlation(new_cor)
            cm.__enter__()
        else:
            cm = None
        try:
            yield span
            if span.status is SpanStatus.UNSET:
                span.set_status(SpanStatus.OK)
        except BaseException as exc:
            span.record_exception(exc)
            raise
        finally:
            span.end(timestamp=self.clock())
            _current_span.reset(token)
            if cm is not None:
                cm.__exit__(None, None, None)
            self._export(span)

    def _export(self, span: Span) -> None:
        for exporter in list(self.exporters):
            try:
                exporter.export(span)
            except Exception:  # noqa: BLE001
                log.exception("observability.tracer.export_failed", exporter=exporter.name)

    # -- convenience --------------------------------------------------- #

    def trace_call(self, name: str, fn: Callable[..., Any], *args, **kwargs) -> Any:
        with self.start_span(name):
            return fn(*args, **kwargs)


# -- default tracer -------------------------------------------------- #

_default_tracer: Tracer | None = None
_default_exporter: InMemorySpanExporter | None = None


def default_tracer() -> Tracer:
    global _default_tracer, _default_exporter
    if _default_tracer is None:
        _default_exporter = InMemorySpanExporter()
        _default_tracer = Tracer(exporters=[_default_exporter])
    return _default_tracer


def default_exporter() -> InMemorySpanExporter:
    default_tracer()
    assert _default_exporter is not None
    return _default_exporter


def set_default_tracer(tracer: Tracer | None) -> Tracer | None:
    global _default_tracer
    prev = _default_tracer
    _default_tracer = tracer
    return prev


def reset_default_tracer() -> None:
    global _default_tracer, _default_exporter
    _default_tracer = None
    _default_exporter = None


__all__ = [
    "InMemorySpanExporter",
    "NoopSpanExporter",
    "SpanExporter",
    "Tracer",
    "current_span",
    "default_exporter",
    "default_tracer",
    "reset_default_tracer",
    "set_default_tracer",
]
