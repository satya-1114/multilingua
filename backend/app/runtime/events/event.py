"""Workflow event model (Phase 8.2).

Generic, transport-agnostic envelope for domain events consumed by the
:class:`~app.runtime.events.dispatcher.WorkflowTriggerDispatcher`.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_correlation_id() -> str:
    return uuid.uuid4().hex


@dataclass(frozen=True, slots=True)
class WorkflowEvent:
    """A single domain event published on the event bus."""

    event_type: str
    organization_id: str | None = None
    actor_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=_utcnow)
    correlation_id: str = field(default_factory=_new_correlation_id)

    def __post_init__(self) -> None:  # pragma: no cover - simple validation
        if not self.event_type or not isinstance(self.event_type, str):
            raise ValueError("event_type must be a non-empty string")

    # -- helpers ---------------------------------------------------------- #

    def to_dict(self) -> dict[str, Any]:
        return {
            "eventType": self.event_type,
            "organizationId": self.organization_id,
            "actorId": self.actor_id,
            "resourceType": self.resource_type,
            "resourceId": self.resource_id,
            "payload": dict(self.payload),
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp.isoformat(),
            "correlationId": self.correlation_id,
        }

    def with_metadata(self, **extra: Any) -> "WorkflowEvent":
        merged = {**self.metadata, **extra}
        return WorkflowEvent(
            event_type=self.event_type,
            organization_id=self.organization_id,
            actor_id=self.actor_id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            payload=dict(self.payload),
            metadata=merged,
            timestamp=self.timestamp,
            correlation_id=self.correlation_id,
        )


__all__ = ["WorkflowEvent"]
