"""Workflow runtime package (Phase 8.1).

Entry points:

* :data:`default_registry` — the module-level action registry.
* :class:`WorkflowRuntimeExecutor` — executes a workflow definition.
* :class:`WorkflowRuntimeService` / :data:`workflow_runtime_service` —
  service facade with :func:`load_default_handlers` for startup.
"""
from __future__ import annotations

from app.runtime.base import BaseActionHandler
from app.runtime.context import WorkflowExecutionContext
from app.runtime.exceptions import (
    ActionExecutionError,
    HandlerRegistrationError,
    InvalidWorkflowError,
    UnknownActionError,
    WorkflowRuntimeError,
)
from app.runtime.executor import WorkflowRuntimeExecutor
from app.runtime.registry import ActionRegistry, default_registry
from app.runtime.result import ActionResult, ExecutionResult
from app.runtime.service import (
    DEFAULT_HANDLERS,
    WorkflowRuntimeService,
    workflow_runtime_service,
)


def load_default_handlers(*, replace: bool = True) -> list[str]:
    """Register the built-in placeholder handlers on the default registry."""
    return workflow_runtime_service.load_handlers(replace=replace)


__all__ = [
    "ActionRegistry",
    "ActionResult",
    "ActionExecutionError",
    "BaseActionHandler",
    "DEFAULT_HANDLERS",
    "ExecutionResult",
    "HandlerRegistrationError",
    "InvalidWorkflowError",
    "UnknownActionError",
    "WorkflowExecutionContext",
    "WorkflowRuntimeError",
    "WorkflowRuntimeExecutor",
    "WorkflowRuntimeService",
    "default_registry",
    "load_default_handlers",
    "workflow_runtime_service",
]
