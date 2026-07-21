"""Automation & Workflow Engine integration facade (Phase 7.4).

Single entry point that fans out workflow lifecycle events into the
existing platform infrastructure:

* **Audit** — :mod:`app.services.audit`
* **Notifications** — :mod:`app.services.notifications`
* **Analytics** — :mod:`app.services.analytics` (platform-scope metrics)
* **Search** — registers a ``workflow`` scope on
  :mod:`app.services.search` at import time.

Design contract
---------------
* Every emitter is best-effort. Notification, audit, or analytics
  failures MUST NOT abort the underlying workflow operation and MUST
  NOT roll back the caller's transaction.
* No downstream integration code lives in the workflow service layer;
  callers invoke the helpers exposed here.
* No scheduler / Celery / webhook / email / SMS delivery lives here —
  that is out of scope for this phase.
"""
from __future__ import annotations

import uuid
from typing import Any, Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.constants.analytics import METRIC_SCOPE_PLATFORM
from app.models.workflow import (
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
)
from app.services import analytics as analytics_service
from app.services import audit as audit_service
from app.services import notifications as notif_service
from app.services import search as search_svc
from app.runtime.events import publish_event as _publish_event

log = get_logger(__name__)

CATEGORY = "workflow"
MODULE_DEFINITION = "workflow_definition"
MODULE_EXECUTION = "workflow_execution"
MODULE_STEP = "workflow_execution_step"


# --------------------------------------------------------------------------- #
# Safe wrappers — every integration path swallows exceptions.
# --------------------------------------------------------------------------- #


def _safe_audit(db: Session, **kwargs: Any) -> None:
    try:
        audit_service.log(db, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("workflow audit emit failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


def _safe_notify(db: Session, *, user_id: Any, **kwargs: Any) -> None:
    if user_id is None:
        return
    if not isinstance(user_id, uuid.UUID):
        try:
            user_id = uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            return
    try:
        notif_service.create(db, user_id=user_id, category=CATEGORY, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("workflow notification emit failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


def _safe_broadcast(
    db: Session,
    recipients: Iterable[Any] | None,
    *,
    title: str,
    message: str,
    priority: str = "normal",
    href: str,
) -> None:
    seen: set[str] = set()
    for uid in recipients or ():
        if uid is None:
            continue
        key = str(uid)
        if key in seen:
            continue
        seen.add(key)
        _safe_notify(
            db, user_id=uid, title=title, message=message,
            priority=priority, href=href,
        )


def _safe_metric(
    db: Session,
    *,
    metric_name: str,
    entity_type: str | None = None,
    entity_id: Any = None,
    metric_value: float = 1.0,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        analytics_service.metric_service.record_metric(
            db,
            metric_name=metric_name,
            metric_scope=METRIC_SCOPE_PLATFORM,
            metric_value=metric_value,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
        )
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("workflow analytics emit failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Reference helpers
# --------------------------------------------------------------------------- #


def _def_href(wf: WorkflowDefinition) -> str:
    return f"/workflows/{wf.id}"


def _exec_href(exe: WorkflowExecution) -> str:
    return f"/workflows/{exe.workflow_definition_id}/executions/{exe.id}"


def _def_label(wf: WorkflowDefinition) -> str:
    return wf.name or f"Workflow {wf.id}"


# --------------------------------------------------------------------------- #
# Definition lifecycle
# --------------------------------------------------------------------------- #


def workflow_created(
    db: Session,
    wf: WorkflowDefinition,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[Any] | None = None,
) -> None:
    _safe_audit(
        db,
        action="create",
        module=MODULE_DEFINITION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(wf.id),
        entity_label=_def_label(wf),
        metadata={"trigger_type": wf.trigger_type, "enabled": wf.enabled},
    )
    _safe_metric(
        db,
        metric_name="workflow.created",
        entity_type="workflow_definition",
        entity_id=wf.id,
        metadata={"trigger_type": wf.trigger_type},
    )
    _publish_event(
        "workflow.created",
        db=db,
        organization_id=wf.organization_id,
        actor_id=actor_id,
        resource_type="workflow_definition",
        resource_id=wf.id,
        payload={"triggerType": wf.trigger_type, "enabled": wf.enabled},
    )


def workflow_updated(
    db: Session,
    wf: WorkflowDefinition,
    *,
    actor_id: uuid.UUID | str | None = None,
    changes: dict[str, Any] | None = None,
) -> None:
    _safe_audit(
        db,
        action="update",
        module=MODULE_DEFINITION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(wf.id),
        entity_label=_def_label(wf),
        metadata={"changes": list((changes or {}).keys())},
    )


def workflow_enabled(
    db: Session,
    wf: WorkflowDefinition,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[Any] | None = None,
) -> None:
    _safe_audit(
        db, action="enable", module=MODULE_DEFINITION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(wf.id), entity_label=_def_label(wf),
    )
    _safe_broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title=f"Workflow enabled: {_def_label(wf)}",
        message="This workflow is now enabled and will respond to triggers.",
        href=_def_href(wf),
    )


def workflow_disabled(
    db: Session,
    wf: WorkflowDefinition,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[Any] | None = None,
) -> None:
    _safe_audit(
        db, action="disable", module=MODULE_DEFINITION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(wf.id), entity_label=_def_label(wf),
    )
    _safe_broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title=f"Workflow disabled: {_def_label(wf)}",
        message="This workflow has been disabled and will not fire on triggers.",
        priority="normal",
        href=_def_href(wf),
    )


def workflow_deleted(
    db: Session,
    wf: WorkflowDefinition,
    *,
    actor_id: uuid.UUID | str | None = None,
) -> None:
    _safe_audit(
        db, action="delete", module=MODULE_DEFINITION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(wf.id), entity_label=_def_label(wf),
    )


# --------------------------------------------------------------------------- #
# Execution lifecycle
# --------------------------------------------------------------------------- #


def execution_started(
    db: Session,
    exe: WorkflowExecution,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[Any] | None = None,
) -> None:
    _safe_audit(
        db, action="start", module=MODULE_EXECUTION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(exe.id),
        metadata={
            "workflow_definition_id": str(exe.workflow_definition_id),
            "trigger_event": exe.trigger_event,
        },
    )
    _safe_metric(
        db,
        metric_name="workflow.executed",
        entity_type="workflow_execution",
        entity_id=exe.id,
        metadata={"workflow_definition_id": str(exe.workflow_definition_id)},
    )
    _safe_broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title="Workflow execution started",
        message="A workflow execution has started.",
        href=_exec_href(exe),
    )


def execution_completed(
    db: Session,
    exe: WorkflowExecution,
    *,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[Any] | None = None,
) -> None:
    _safe_audit(
        db, action="complete", module=MODULE_EXECUTION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(exe.id),
    )
    _safe_metric(
        db,
        metric_name="workflow.completed",
        entity_type="workflow_execution",
        entity_id=exe.id,
    )
    _safe_broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title="Workflow execution completed",
        message="A workflow execution has finished successfully.",
        priority="low",
        href=_exec_href(exe),
    )
    _publish_event(
        "workflow.execution.completed",
        db=db,
        actor_id=actor_id,
        resource_type="workflow_execution",
        resource_id=exe.id,
        payload={"workflowDefinitionId": str(exe.workflow_definition_id)},
    )


def execution_failed(
    db: Session,
    exe: WorkflowExecution,
    *,
    reason: str | None = None,
    actor_id: uuid.UUID | str | None = None,
    notify_user_ids: Iterable[Any] | None = None,
) -> None:
    _safe_audit(
        db, action="fail", module=MODULE_EXECUTION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(exe.id),
        metadata={"reason": reason} if reason is not None else None,
    )
    _safe_metric(
        db,
        metric_name="workflow.failed",
        entity_type="workflow_execution",
        entity_id=exe.id,
        metadata={"reason": reason} if reason is not None else None,
    )
    _safe_broadcast(
        db, [actor_id, *(notify_user_ids or ())],
        title="Workflow execution failed",
        message=reason or "A workflow execution failed.",
        priority="high",
        href=_exec_href(exe),
    )
    _publish_event(
        "workflow.execution.failed",
        db=db,
        actor_id=actor_id,
        resource_type="workflow_execution",
        resource_id=exe.id,
        payload={
            "workflowDefinitionId": str(exe.workflow_definition_id),
            "reason": reason,
        },
    )


def execution_cancelled(
    db: Session,
    exe: WorkflowExecution,
    *,
    reason: str | None = None,
    actor_id: uuid.UUID | str | None = None,
) -> None:
    _safe_audit(
        db, action="cancel", module=MODULE_EXECUTION,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(exe.id),
        metadata={"reason": reason} if reason is not None else None,
    )


# --------------------------------------------------------------------------- #
# Step retry
# --------------------------------------------------------------------------- #


def step_retried(
    db: Session,
    step: WorkflowExecutionStep,
    *,
    actor_id: uuid.UUID | str | None = None,
) -> None:
    _safe_audit(
        db, action="retry", module=MODULE_STEP,
        actor_id=actor_id if isinstance(actor_id, uuid.UUID) else None,
        entity_id=str(step.id),
        metadata={"retry_count": step.retry_count},
    )
    _safe_metric(
        db,
        metric_name="workflow.retry",
        entity_type="workflow_execution_step",
        entity_id=step.id,
        metric_value=float(step.retry_count or 1),
        metadata={"execution_id": str(step.workflow_execution_id)},
    )


# --------------------------------------------------------------------------- #
# Search registration
# --------------------------------------------------------------------------- #


def _search_workflow(
    db: Session,
    q: str,
    workspace_id: str | None,
    limit: int,
) -> list[dict]:
    """Combined search over workflow definitions and executions."""
    per = max(1, limit // 2) or 1
    hits: list[dict] = []
    like = f"%{q.strip()}%"

    defs = db.scalars(
        select(WorkflowDefinition).where(or_(
            WorkflowDefinition.name.ilike(like),
            WorkflowDefinition.description.ilike(like),
            WorkflowDefinition.trigger_type.ilike(like),
        )).limit(per)
    )
    for wf in defs:
        hits.append({
            "scope": "workflow",
            "id": str(wf.id),
            "title": f"workflow · {wf.name}",
            "subtitle": f"{wf.trigger_type} · {'enabled' if wf.enabled else 'disabled'}",
            "href": _def_href(wf),
            "score": 2.0 if q.lower() in (wf.name or "").lower() else 1.0,
        })

    execs = db.scalars(
        select(WorkflowExecution).where(or_(
            WorkflowExecution.status.ilike(like),
            WorkflowExecution.trigger_event.ilike(like),
        )).limit(per)
    )
    for exe in execs:
        hits.append({
            "scope": "workflow",
            "id": str(exe.id),
            "title": f"execution · {exe.status}",
            "subtitle": exe.trigger_event,
            "href": _exec_href(exe),
            "score": 1.0,
        })

    return hits[:limit]


def register_search() -> None:
    """Register the ``workflow`` scope on the shared search registry.

    Safe to call multiple times — idempotent.
    """
    search_svc.SCOPE_PERMISSIONS["workflow"] = "workflow:view"
    search_svc._HANDLERS["workflow"] = _search_workflow


# Register at import so the scope is available anywhere the events
# module is imported (routers, tests, workers).
register_search()


__all__ = [
    "CATEGORY",
    "MODULE_DEFINITION",
    "MODULE_EXECUTION",
    "MODULE_STEP",
    "workflow_created",
    "workflow_updated",
    "workflow_enabled",
    "workflow_disabled",
    "workflow_deleted",
    "execution_started",
    "execution_completed",
    "execution_failed",
    "execution_cancelled",
    "step_retried",
    "register_search",
]
