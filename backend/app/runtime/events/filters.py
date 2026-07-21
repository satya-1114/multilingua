"""Trigger filter engine (Phase 8.2).

Given a :class:`WorkflowEvent` and a :class:`WorkflowTrigger`, decide
whether the trigger should fire. Deliberately simple and pure —
future condition DSLs plug in here without touching the dispatcher.

Supported `conditions_json` keys
--------------------------------
* ``organization_id``  — must equal event.organization_id (or event
  organization is None and trigger accepts any).
* ``resource_type``    — must equal event.resource_type.
* ``resource_id``      — must equal event.resource_id.
* ``actor_id``         — must equal event.actor_id.
* ``payload``          — dict of {field: expected_value} — every field
  must match ``event.payload[field]`` exactly.
* ``payload_in``       — dict of {field: [allowed values]} — event
  value must be one of the listed values.
* ``metadata``         — same shape as ``payload``, matched against
  event.metadata.
"""
from __future__ import annotations

from typing import Any

from app.models.workflow import WorkflowTrigger

from .event import WorkflowEvent


def _match_field(event_value: Any, expected: Any) -> bool:
    if expected is None:
        return True
    return event_value == expected


def _match_mapping(
    event_map: dict[str, Any], expected: dict[str, Any] | None
) -> bool:
    if not expected:
        return True
    for key, value in expected.items():
        if event_map.get(key) != value:
            return False
    return True


def _match_in(
    event_map: dict[str, Any], expected: dict[str, list[Any]] | None
) -> bool:
    if not expected:
        return True
    for key, allowed in expected.items():
        if not isinstance(allowed, (list, tuple, set)):
            return False
        if event_map.get(key) not in allowed:
            return False
    return True


def trigger_matches_event(trigger: WorkflowTrigger, event: WorkflowEvent) -> bool:
    """Return True when *trigger* should fire for *event*."""
    if trigger.event_name != event.event_type:
        return False
    if trigger.event_source and event.resource_type and (
        trigger.event_source != event.resource_type
    ):
        return False

    conditions: dict[str, Any] = trigger.conditions_json or {}

    if not _match_field(event.organization_id, conditions.get("organization_id")):
        return False
    if not _match_field(event.resource_type, conditions.get("resource_type")):
        return False
    if not _match_field(event.resource_id, conditions.get("resource_id")):
        return False
    if not _match_field(event.actor_id, conditions.get("actor_id")):
        return False
    if not _match_mapping(event.payload or {}, conditions.get("payload")):
        return False
    if not _match_in(event.payload or {}, conditions.get("payload_in")):
        return False
    if not _match_mapping(event.metadata or {}, conditions.get("metadata")):
        return False

    return True


__all__ = ["trigger_matches_event"]
