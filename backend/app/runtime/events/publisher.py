"""Convenience publisher helpers (Phase 8.2).

Module code doesn't need to know about the bus singleton or how to
build :class:`WorkflowEvent` instances. It calls :func:`publish_event`
with the domain fields; wiring lives in one place.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger

from .bus import WorkflowEventBus, default_event_bus
from .event import WorkflowEvent

log = get_logger(__name__)


def build_event(
    event_type: str,
    *,
    organization_id: Any | None = None,
    actor_id: Any | None = None,
    resource_type: str | None = None,
    resource_id: Any | None = None,
    payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> WorkflowEvent:
    kwargs: dict[str, Any] = {
        "event_type": event_type,
        "organization_id": _to_str(organization_id),
        "actor_id": _to_str(actor_id),
        "resource_type": resource_type,
        "resource_id": _to_str(resource_id),
        "payload": dict(payload or {}),
        "metadata": dict(metadata or {}),
    }
    if correlation_id:
        kwargs["correlation_id"] = correlation_id
    return WorkflowEvent(**kwargs)


def publish_event(
    event_type: str,
    *,
    db: Session | None = None,
    bus: WorkflowEventBus | None = None,
    organization_id: Any | None = None,
    actor_id: Any | None = None,
    resource_type: str | None = None,
    resource_id: Any | None = None,
    payload: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> WorkflowEvent:
    """Build and publish a :class:`WorkflowEvent`.

    Failures during dispatch are swallowed — publishing is best-effort
    and never blocks the caller's business flow.
    """
    event = build_event(
        event_type,
        organization_id=organization_id,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        metadata=metadata,
        correlation_id=correlation_id,
    )
    target = bus or default_event_bus
    try:
        target.publish(event, context={"db": db} if db is not None else {})
    except Exception:  # pragma: no cover — bus swallows too
        log.exception(
            "publish_event.failed",
            event_type=event_type,
            correlation_id=event.correlation_id,
        )
    return event


def _to_str(value: Any | None) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = ["build_event", "publish_event"]
