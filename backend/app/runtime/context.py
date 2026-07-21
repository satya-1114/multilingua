"""Workflow execution context (Phase 8.1).

Carries every piece of state a handler needs during execution. The
context is intentionally frozen — handlers should record output in the
:class:`ActionResult` they return rather than mutating the context.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.models.workflow import WorkflowDefinition, WorkflowExecution


@dataclass(frozen=True)
class WorkflowExecutionContext:
    workflow: WorkflowDefinition
    execution: WorkflowExecution | None
    organization_id: uuid.UUID | str | None = None
    actor_id: uuid.UUID | str | None = None
    trigger_event: str | None = None
    trigger_payload: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    db: Any | None = None
    logger: structlog.stdlib.BoundLogger = field(
        default_factory=lambda: structlog.get_logger("workflow.runtime")
    )

    @property
    def workflow_id(self) -> str:
        return str(self.workflow.id)

    @property
    def execution_id(self) -> str | None:
        return str(self.execution.id) if self.execution is not None else None

    def bind_logger(self, **kwargs: Any) -> structlog.stdlib.BoundLogger:
        return self.logger.bind(**kwargs)

    @property
    def dry_run(self) -> bool:
        """True when handlers should skip real side effects."""
        return bool(self.metadata.get("dry_run"))


__all__ = ["WorkflowExecutionContext"]
