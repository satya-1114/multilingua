"""Workflow event bus (Phase 8.2).

Synchronous, in-process fan-out. Subscribers can register for a
specific ``event_type`` or the wildcard ``"*"``. Every subscriber runs
inside a try/except boundary — a failing subscriber never blocks
sibling subscribers and never raises to the publisher.
"""
from __future__ import annotations

import time
from threading import RLock
from typing import Any, Callable

from app.core.logging import get_logger

from .event import WorkflowEvent

log = get_logger(__name__)

WILDCARD = "*"

SubscriberFn = Callable[[WorkflowEvent, dict[str, Any]], None]


class WorkflowEventBus:
    """Synchronous in-process publish/subscribe bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[tuple[str, SubscriberFn]]] = {}
        self._lock = RLock()

    # -- registration ----------------------------------------------------- #

    def subscribe(
        self,
        event_type: str,
        subscriber: SubscriberFn,
        *,
        name: str | None = None,
    ) -> str:
        if not event_type:
            raise ValueError("event_type must be a non-empty string")
        if not callable(subscriber):
            raise TypeError("subscriber must be callable")
        sub_name = name or getattr(subscriber, "__name__", "subscriber")
        with self._lock:
            self._subscribers.setdefault(event_type, []).append((sub_name, subscriber))
        log.info(
            "event_bus.subscribe",
            event_type=event_type,
            subscriber=sub_name,
        )
        return sub_name

    def unsubscribe(self, event_type: str, subscriber: SubscriberFn) -> bool:
        with self._lock:
            bucket = self._subscribers.get(event_type, [])
            for i, (_, fn) in enumerate(bucket):
                if fn is subscriber:
                    bucket.pop(i)
                    log.info(
                        "event_bus.unsubscribe",
                        event_type=event_type,
                        subscriber=getattr(subscriber, "__name__", "subscriber"),
                    )
                    return True
        return False

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()

    def list_subscribers(
        self, event_type: str | None = None
    ) -> dict[str, list[str]]:
        with self._lock:
            if event_type is None:
                return {k: [n for n, _ in v] for k, v in self._subscribers.items()}
            return {event_type: [n for n, _ in self._subscribers.get(event_type, [])]}

    # -- publishing ------------------------------------------------------- #

    def publish(
        self,
        event: WorkflowEvent,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Publish *event*, invoking all matching subscribers.

        Returns a per-subscriber diagnostic list (name, duration, ok).
        """
        return self.dispatch(event, context=context)

    def dispatch(
        self,
        event: WorkflowEvent,
        *,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        ctx: dict[str, Any] = context or {}
        with self._lock:
            targets = list(self._subscribers.get(event.event_type, [])) + list(
                self._subscribers.get(WILDCARD, [])
            )
        results: list[dict[str, Any]] = []
        if not targets:
            log.info(
                "event_bus.publish.no_subscribers",
                event_type=event.event_type,
                correlation_id=event.correlation_id,
            )
            return results
        for name, fn in targets:
            started = time.perf_counter()
            try:
                fn(event, ctx)
                ok = True
                error: str | None = None
            except Exception as exc:  # noqa: BLE001 — isolation
                ok = False
                error = str(exc)
                log.exception(
                    "event_bus.subscriber.error",
                    subscriber=name,
                    event_type=event.event_type,
                    correlation_id=event.correlation_id,
                )
            duration = time.perf_counter() - started
            log.info(
                "event_bus.subscriber.dispatched",
                subscriber=name,
                event_type=event.event_type,
                correlation_id=event.correlation_id,
                duration=duration,
                ok=ok,
            )
            results.append(
                {"subscriber": name, "ok": ok, "duration": duration, "error": error}
            )
        return results


#: Module-level default bus wired at application startup.
default_event_bus = WorkflowEventBus()


__all__ = ["WorkflowEventBus", "default_event_bus", "WILDCARD", "SubscriberFn"]
