"""Shared placeholder handler used by Phase 8.1 skeleton handlers.

Each concrete handler subclass sets ``action_type`` and optionally
overrides :meth:`validate`. Real business logic lands in Phase 8.2+.
"""
from __future__ import annotations

from typing import Any, Iterable

from app.constants.workflow import STEP_STATUS_COMPLETED
from app.core.exceptions import ValidationError
from app.runtime.base import BaseActionHandler
from app.runtime.context import WorkflowExecutionContext
from app.runtime.result import ActionResult, _now


class PlaceholderActionHandler(BaseActionHandler):
    """Base for skeleton handlers — logs and returns success."""

    #: Required config keys — subclasses may override.
    required_keys: tuple[str, ...] = ()

    def validate(self, config: dict[str, Any]) -> None:
        missing: list[str] = [k for k in self.required_keys if k not in config]
        if missing:
            raise ValidationError(
                f"{self.action_type}: missing required configuration",
                details={"missing": missing},
            )

    def execute(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> ActionResult:
        self.validate(config)
        started = _now()
        log = context.bind_logger(
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            action_type=self.action_type,
            handler=self.name,
        )
        log.info("workflow.action.execute", config_keys=sorted(config.keys()))
        completed = _now()
        return ActionResult(
            action_type=self.action_type,
            success=True,
            status=STEP_STATUS_COMPLETED,
            started_at=started,
            completed_at=completed,
            output={"placeholder": True, "handler": self.name},
            handler=self.name,
        )


def _as_tuple(keys: Iterable[str]) -> tuple[str, ...]:
    return tuple(keys)


__all__ = ["PlaceholderActionHandler", "_as_tuple"]
