"""Runtime exception hierarchy (Phase 8.1).

All runtime errors derive from :class:`WorkflowRuntimeError` so callers
can distinguish runtime failures from service-layer validation/CRUD
errors.
"""
from __future__ import annotations

from typing import Any


class WorkflowRuntimeError(Exception):
    """Base class for all workflow runtime errors."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidWorkflowError(WorkflowRuntimeError):
    """Workflow definition is invalid for execution."""


class UnknownActionError(WorkflowRuntimeError):
    """No handler is registered for the requested action type."""


class HandlerRegistrationError(WorkflowRuntimeError):
    """A handler could not be registered (duplicate / invalid)."""


class ActionExecutionError(WorkflowRuntimeError):
    """A handler raised while executing an action."""

    def __init__(
        self,
        message: str,
        *,
        action_type: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.action_type = action_type
        self.retryable = retryable


__all__ = [
    "WorkflowRuntimeError",
    "InvalidWorkflowError",
    "UnknownActionError",
    "HandlerRegistrationError",
    "ActionExecutionError",
]
