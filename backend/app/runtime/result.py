"""Runtime result objects (Phase 8.1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ActionResult:
    """The outcome of executing a single workflow action."""

    action_type: str
    success: bool
    status: str  # matches STEP_STATUS_*
    started_at: datetime
    completed_at: datetime
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    retryable: bool = False
    action_id: str | None = None
    handler: str | None = None

    @property
    def duration(self) -> float:
        """Elapsed seconds between started_at and completed_at."""
        return max((self.completed_at - self.started_at).total_seconds(), 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionType": self.action_type,
            "actionId": self.action_id,
            "handler": self.handler,
            "success": self.success,
            "status": self.status,
            "startedAt": self.started_at.isoformat(),
            "completedAt": self.completed_at.isoformat(),
            "duration": self.duration,
            "output": self.output,
            "error": self.error,
            "retryable": self.retryable,
        }


@dataclass
class ExecutionResult:
    """The outcome of executing an entire workflow."""

    workflow_id: str
    execution_id: str | None
    success: bool
    status: str  # matches WORKFLOW_STATUS_*
    started_at: datetime
    completed_at: datetime
    steps: list[ActionResult] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return max((self.completed_at - self.started_at).total_seconds(), 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflowId": self.workflow_id,
            "executionId": self.execution_id,
            "success": self.success,
            "status": self.status,
            "startedAt": self.started_at.isoformat(),
            "completedAt": self.completed_at.isoformat(),
            "duration": self.duration,
            "error": self.error,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
        }


__all__ = ["ActionResult", "ExecutionResult", "_now"]
