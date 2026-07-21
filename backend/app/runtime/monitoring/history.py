"""Retry history read model (Phase 8.5).

Exposes the persisted step-level retry state for a workflow execution.
All data is sourced from :class:`WorkflowExecutionStep`; no additional
tables are introduced. The service returns plain dicts (camelCase) so
it can be returned directly from the runtime API.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.workflow import (
    workflow_execution_steps as _steps_repo,
    workflow_executions as _executions_repo,
)


def _iso(dt: Any) -> str | None:
    return dt.isoformat() if dt is not None else None


class ExecutionRetryHistoryService:
    """Read-only view of retry metadata for an execution."""

    def __init__(
        self,
        executions_repo=_executions_repo,
        steps_repo=_steps_repo,
    ) -> None:
        self.executions_repo = executions_repo
        self.steps_repo = steps_repo

    def get_retry_history(
        self,
        db: Session,
        execution_id: uuid.UUID | str,
    ) -> dict[str, Any]:
        exe = self.executions_repo.get_execution(db, execution_id)
        if exe is None:
            raise NotFoundError("Execution not found")

        steps, _total = self.steps_repo.list_steps(
            db,
            workflow_execution_id=exe.id,
            page=1,
            page_size=500,
        )

        entries: list[dict[str, Any]] = []
        total_retries = 0
        for step in steps:
            retry_count = int(step.retry_count or 0)
            total_retries += retry_count
            entries.append(
                {
                    "stepId": str(step.id),
                    "actionId": str(step.workflow_action_id),
                    "attempt": retry_count + 1,
                    "retryCount": retry_count,
                    "status": step.status,
                    "finalStatus": step.status
                    if step.status in {"completed", "failed", "skipped"}
                    else None,
                    "lastError": step.error_message,
                    "startedAt": _iso(step.started_at),
                    "completedAt": _iso(step.completed_at),
                }
            )

        return {
            "executionId": str(exe.id),
            "workflowDefinitionId": str(exe.workflow_definition_id),
            "status": exe.status,
            "totalSteps": len(entries),
            "totalRetries": total_retries,
            "steps": entries,
        }


retry_history_service = ExecutionRetryHistoryService()


__all__ = ["ExecutionRetryHistoryService", "retry_history_service"]