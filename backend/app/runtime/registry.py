"""Action handler registry (Phase 8.1).

Runtime lookup table that maps ``action_type`` -> handler instance.
Registrations happen during application startup via
:func:`app.runtime.load_default_handlers`.
"""
from __future__ import annotations

from typing import Any

from app.runtime.base import BaseActionHandler
from app.runtime.context import WorkflowExecutionContext
from app.runtime.exceptions import (
    HandlerRegistrationError,
    UnknownActionError,
)
from app.runtime.result import ActionResult


class ActionRegistry:
    """In-memory registry of action handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, BaseActionHandler] = {}

    # -- registration ----------------------------------------------------- #

    def register(
        self,
        action_type: str,
        handler: BaseActionHandler,
        *,
        replace: bool = False,
    ) -> None:
        if not action_type or not isinstance(action_type, str):
            raise HandlerRegistrationError("action_type must be a non-empty string")
        if not isinstance(handler, BaseActionHandler):
            raise HandlerRegistrationError(
                "handler must inherit from BaseActionHandler",
                details={"got": type(handler).__name__},
            )
        if action_type in self._handlers and not replace:
            raise HandlerRegistrationError(
                f"Handler already registered for {action_type!r}",
                details={"action_type": action_type},
            )
        self._handlers[action_type] = handler

    def unregister(self, action_type: str) -> None:
        self._handlers.pop(action_type, None)

    def clear(self) -> None:
        self._handlers.clear()

    # -- lookup ----------------------------------------------------------- #

    def get(self, action_type: str) -> BaseActionHandler:
        try:
            return self._handlers[action_type]
        except KeyError as exc:
            raise UnknownActionError(
                f"No handler registered for action type {action_type!r}",
                details={"action_type": action_type},
            ) from exc

    def has(self, action_type: str) -> bool:
        return action_type in self._handlers

    def registered_types(self) -> list[str]:
        return sorted(self._handlers.keys())

    # -- execution helper ------------------------------------------------- #

    def execute(
        self,
        action_type: str,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> ActionResult:
        handler = self.get(action_type)
        return handler.execute(context, config)


#: Module-level default registry populated at startup.
default_registry = ActionRegistry()


__all__ = ["ActionRegistry", "default_registry"]
