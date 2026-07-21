"""Abstract action handler base class (Phase 8.1)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.runtime.context import WorkflowExecutionContext
from app.runtime.result import ActionResult


class BaseActionHandler(ABC):
    """Contract every action handler must implement."""

    #: Human-readable identifier surfaced in logs / registry listings.
    action_type: str = ""

    def validate(self, config: dict[str, Any]) -> None:  # noqa: B027 - optional override
        """Validate handler configuration. Raise ValidationError on failure."""

    @abstractmethod
    def execute(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> ActionResult:
        """Execute the action and return its result."""

    def supports_retry(self) -> bool:
        """Whether the runtime may retry this handler on failure."""
        return True

    def rollback(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
        result: ActionResult,
    ) -> None:  # noqa: B027 - placeholder for future compensation logic
        """Optional compensation hook — implemented by handlers that need it."""

    @property
    def name(self) -> str:
        return self.__class__.__name__


__all__ = ["BaseActionHandler"]
