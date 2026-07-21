"""Span primitives used by the tracing abstraction (Phase 9.3)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanEvent:
    name: str
    timestamp: float
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "attributes": dict(self.attributes),
        }


@dataclass
class SpanContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id,
        }


@dataclass
class Span:
    """In-memory span record."""

    name: str
    context: SpanContext
    started_at: float
    ended_at: float | None = None
    status: SpanStatus = SpanStatus.UNSET
    status_message: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    exception: str | None = None

    # -- lifecycle ------------------------------------------------------ #

    def set_attribute(self, key: str, value: Any) -> "Span":
        self.attributes[str(key)] = value
        return self

    def set_attributes(self, mapping: dict[str, Any]) -> "Span":
        for k, v in (mapping or {}).items():
            self.set_attribute(k, v)
        return self

    def add_event(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        timestamp: float | None = None,
    ) -> SpanEvent:
        evt = SpanEvent(
            name=name,
            timestamp=timestamp if timestamp is not None else time.time(),
            attributes=dict(attributes or {}),
        )
        self.events.append(evt)
        return evt

    def set_status(self, status: SpanStatus, message: str | None = None) -> "Span":
        self.status = status
        self.status_message = message
        return self

    def record_exception(self, exc: BaseException) -> None:
        self.exception = f"{type(exc).__name__}: {exc}"
        self.set_status(SpanStatus.ERROR, str(exc))
        self.add_event(
            "exception",
            attributes={"exception.type": type(exc).__name__, "exception.message": str(exc)},
        )

    def end(self, *, timestamp: float | None = None) -> None:
        if self.ended_at is not None:
            return
        self.ended_at = timestamp if timestamp is not None else time.time()
        if self.status is SpanStatus.UNSET:
            self.status = SpanStatus.OK

    @property
    def duration(self) -> float:
        if self.ended_at is None:
            return 0.0
        return max(self.ended_at - self.started_at, 0.0)

    @property
    def is_ended(self) -> bool:
        return self.ended_at is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "context": self.context.to_dict(),
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
            "duration": self.duration,
            "status": self.status.value,
            "statusMessage": self.status_message,
            "attributes": dict(self.attributes),
            "events": [e.to_dict() for e in self.events],
            "exception": self.exception,
        }


__all__ = ["Span", "SpanContext", "SpanEvent", "SpanStatus"]
