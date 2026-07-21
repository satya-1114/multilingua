"""Statistics service for the workflow runtime (Phase 8.5)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.workflow import (
    WORKFLOW_STATUS_CANCELLED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_RUNNING,
)
from app.models.workflow import (
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
)


def _rate(part: int, total: int) -> float:
    return round(part / total, 6) if total else 0.0


class WorkflowStatisticsService:
    """Read model over persisted execution data."""

    def overview(
        self,
        db: Session,
        *,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        status_stmt = (
            select(WorkflowExecution.status, func.count(WorkflowExecution.id))
            .where(WorkflowExecution.deleted_at.is_(None))
            .group_by(WorkflowExecution.status)
        )
        if since is not None:
            status_stmt = status_stmt.where(WorkflowExecution.created_at >= since)
        by_status: dict[str, int] = {row[0]: int(row[1]) for row in db.execute(status_stmt)}

        completed = by_status.get(WORKFLOW_STATUS_COMPLETED, 0)
        failed = by_status.get(WORKFLOW_STATUS_FAILED, 0)
        cancelled = by_status.get(WORKFLOW_STATUS_CANCELLED, 0)
        running = by_status.get(WORKFLOW_STATUS_RUNNING, 0)
        total = sum(by_status.values())

        dur_stmt = select(
            WorkflowExecution.started_at, WorkflowExecution.completed_at
        ).where(
            WorkflowExecution.deleted_at.is_(None),
            WorkflowExecution.started_at.is_not(None),
            WorkflowExecution.completed_at.is_not(None),
        )
        if since is not None:
            dur_stmt = dur_stmt.where(WorkflowExecution.created_at >= since)
        durations: list[float] = []
        for started_at, completed_at in db.execute(dur_stmt):
            if started_at is None or completed_at is None:
                continue
            durations.append(max((completed_at - started_at).total_seconds(), 0.0))
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        retry_exe_stmt = select(
            func.count(func.distinct(WorkflowExecutionStep.workflow_execution_id))
        ).where(
            WorkflowExecutionStep.deleted_at.is_(None),
            WorkflowExecutionStep.retry_count > 0,
        )
        retry_executions = int(db.scalar(retry_exe_stmt) or 0)

        total_retries_stmt = select(
            func.coalesce(func.sum(WorkflowExecutionStep.retry_count), 0)
        ).where(WorkflowExecutionStep.deleted_at.is_(None))
        total_retries = int(db.scalar(total_retries_stmt) or 0)

        return {
            "total": total,
            "byStatus": by_status,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "running": running,
            "successRate": _rate(completed, total),
            "failureRate": _rate(failed, total),
            "retryRate": _rate(retry_executions, total),
            "avgDurationSeconds": round(avg_duration, 6),
            "totalRetries": total_retries,
            "retryExecutions": retry_executions,
            "since": since.isoformat() if since is not None else None,
        }

    def top_workflows(
        self, db: Session, *, limit: int = 5
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                WorkflowExecution.workflow_definition_id,
                func.count(WorkflowExecution.id).label("total"),
            )
            .where(WorkflowExecution.deleted_at.is_(None))
            .group_by(WorkflowExecution.workflow_definition_id)
            .order_by(func.count(WorkflowExecution.id).desc())
            .limit(max(1, int(limit)))
        )
        rows = list(db.execute(stmt))
        return [
            {
                "workflowDefinitionId": str(wf_id),
                "name": self._resolve_name(db, wf_id),
                "total": int(total),
            }
            for wf_id, total in rows
        ]

    def top_failures(
        self, db: Session, *, limit: int = 5
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                WorkflowExecution.workflow_definition_id,
                func.count(WorkflowExecution.id).label("failed"),
            )
            .where(
                WorkflowExecution.deleted_at.is_(None),
                WorkflowExecution.status == WORKFLOW_STATUS_FAILED,
            )
            .group_by(WorkflowExecution.workflow_definition_id)
            .order_by(func.count(WorkflowExecution.id).desc())
            .limit(max(1, int(limit)))
        )
        rows = list(db.execute(stmt))
        return [
            {
                "workflowDefinitionId": str(wf_id),
                "name": self._resolve_name(db, wf_id),
                "failed": int(failed),
            }
            for wf_id, failed in rows
        ]

    def _resolve_name(self, db: Session, wf_id: Any) -> str | None:
        if wf_id is None:
            return None
        row = db.execute(
            select(WorkflowDefinition.name).where(WorkflowDefinition.id == wf_id)
        ).first()
        return row[0] if row else None


workflow_statistics_service = WorkflowStatisticsService()


__all__ = ["WorkflowStatisticsService", "workflow_statistics_service"]