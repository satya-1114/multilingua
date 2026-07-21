"""Bus subscriber wiring (Phase 8.2).

Registers the :class:`WorkflowTriggerDispatcher` on the default event
bus using the wildcard subscription. Called once at application
startup — safe to call multiple times (idempotent).
"""
from __future__ import annotations

from app.core.logging import get_logger

from .bus import WILDCARD, WorkflowEventBus, default_event_bus
from .dispatcher import WorkflowTriggerDispatcher, default_dispatcher

log = get_logger(__name__)

_INSTALLED_FLAG = "_workflow_dispatcher_installed"


def install_default_subscribers(
    bus: WorkflowEventBus | None = None,
    *,
    dispatcher: WorkflowTriggerDispatcher | None = None,
) -> bool:
    """Install the trigger dispatcher as a wildcard subscriber.

    Returns ``True`` when a fresh subscription was added, ``False`` if
    it was already installed on this bus.
    """
    target = bus or default_event_bus
    if getattr(target, _INSTALLED_FLAG, False):
        return False
    disp = dispatcher or default_dispatcher
    target.subscribe(WILDCARD, disp, name="WorkflowTriggerDispatcher")
    setattr(target, _INSTALLED_FLAG, True)
    log.info("event_bus.default_subscribers.installed")
    return True


def uninstall_default_subscribers(bus: WorkflowEventBus | None = None) -> None:
    target = bus or default_event_bus
    try:
        target.unsubscribe(WILDCARD, default_dispatcher)
    except Exception:  # pragma: no cover
        pass
    if hasattr(target, _INSTALLED_FLAG):
        delattr(target, _INSTALLED_FLAG)


__all__ = ["install_default_subscribers", "uninstall_default_subscribers"]
