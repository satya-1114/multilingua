"""Workflow event bus package (Phase 8.2)."""
from __future__ import annotations

from .bus import WILDCARD, WorkflowEventBus, default_event_bus
from .dispatcher import WorkflowTriggerDispatcher, default_dispatcher
from .event import WorkflowEvent
from .filters import trigger_matches_event
from .publisher import build_event, publish_event
from .subscribers import install_default_subscribers, uninstall_default_subscribers

__all__ = [
    "WILDCARD",
    "WorkflowEventBus",
    "WorkflowEvent",
    "WorkflowTriggerDispatcher",
    "build_event",
    "default_dispatcher",
    "default_event_bus",
    "install_default_subscribers",
    "publish_event",
    "trigger_matches_event",
    "uninstall_default_subscribers",
]
