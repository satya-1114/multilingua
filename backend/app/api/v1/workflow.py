"""FastAPI router for the Automation & Workflow Engine (Phase 7.3).

Thin transport layer over `app.services.workflow`. All validation,
transition, and RBAC-domain rules live in the service layer. This
module only:

* Wires dependency-injected DB/user/permission checks.
* Parses request bodies / query params.
* Serialises ORM objects into the platform-standard camelCase envelope
  via ``ok()`` / ``paginated()``.

No event execution, scheduling, Celery, notifications, webhooks,
email, SMS, or analytics integration happens here — those are later
phases and out of scope for 7.3.

Route registration order note
-----------------------------
FastAPI matches routes in registration order. The literal-prefix
routes (``/triggers/{triggerId}``, ``/actions/{actionId}``,
``/executions/{executionId}``, ``/steps/{stepId}``) MUST be
registered before the parameterised ``/{workflow_id}`` routes,
otherwise ``/workflows/triggers/{id}`` would be captured as a
workflow_id lookup.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.models.user import User
from app.models.workflow import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTrigger,
)
from app.schemas.workflow import (
    WorkflowActionCreate,
    WorkflowActionUpdate,
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    WorkflowExecutionCreate,
    WorkflowExecutionUpdate,
    WorkflowExecutionStepCreate,
    WorkflowExecutionStepUpdate,
    WorkflowTriggerCreate,
    WorkflowTriggerUpdate,
)
from app.services.workflow import (
    workflow_action_service as _actions,
    workflow_definition_service as _defs,
    workflow_execution_service as _executions,
    workflow_trigger_service as _triggers,
)

router = APIRouter()


# --------------------------------------------------------------------------- #
# Serialisers
# --------------------------------------------------------------------------- #


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _sid(v: Any) -> str | None:
    return str(v) if v is not None else None


def _s_definition(wf: WorkflowDefinition) -> dict[str, Any]:
    return {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description,
        "triggerType": wf.trigger_type,
        "enabled": wf.enabled,
        "organizationId": _sid(wf.organization_id),
        "version": wf.version,
        "metadata": dict(wf.metadata_ or {}),
        "createdAt": _iso(wf.created_at),
        "updatedAt": _iso(wf.updated_at),
    }


def _s_trigger(t: WorkflowTrigger) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "workflowDefinitionId": str(t.workflow_definition_id),
        "eventName": t.event_name,
        "eventSource": t.event_source,
        "conditionsJson": dict(t.conditions_json or {}),
        "metadata": dict(t.metadata_ or {}),
        "createdAt": _iso(t.created_at),
        "updatedAt": _iso(t.updated_at),
    }


def _s_action(a: WorkflowAction) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "workflowDefinitionId": str(a.workflow_definition_id),
        "sequence": a.sequence,
        "actionType": a.action_type,
        "configurationJson": dict(a.configuration_json or {}),
        "enabled": a.enabled,
        "metadata": dict(a.metadata_ or {}),
        "createdAt": _iso(a.created_at),
        "updatedAt": _iso(a.updated_at),
    }


def _s_execution(e: WorkflowExecution) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "workflowDefinitionId": str(e.workflow_definition_id),
        "triggerEvent": e.trigger_event,
        "status": e.status,
        "startedAt": _iso(e.started_at),
        "completedAt": _iso(e.completed_at),
        "failureReason": e.failure_reason,
        "contextJson": dict(e.context_json or {}),
        "metadata": dict(e.metadata_ or {}),
        "createdAt": _iso(e.created_at),
        "updatedAt": _iso(e.updated_at),
    }


def _s_step(s: WorkflowExecutionStep) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "workflowExecutionId": str(s.workflow_execution_id),
        "workflowActionId": str(s.workflow_action_id),
        "status": s.status,
        "startedAt": _iso(s.started_at),
        "completedAt": _iso(s.completed_at),
        "retryCount": s.retry_count,
        "outputJson": dict(s.output_json or {}),
        "errorMessage": s.error_message,
        "metadata": dict(s.metadata_ or {}),
        "createdAt": _iso(s.created_at),
        "updatedAt": _iso(s.updated_at),
    }


# =========================================================================== #
# TRIGGERS — literal-prefix routes registered FIRST (must beat /{workflow_id}) #
# =========================================================================== #


@router.get("/triggers/{trigger_id}", response_model=None, summary="Get trigger")
def get_trigger(
    trigger_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    return ok(_s_trigger(_triggers.get_trigger(db, trigger_id)))


@router.patch("/triggers/{trigger_id}", response_model=None, summary="Update trigger")
def update_trigger(
    trigger_id: uuid.UUID,
    payload: WorkflowTriggerUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:update")),
):
    obj = _triggers.update_trigger(
        db,
        trigger_id,
        event_name=payload.eventName,
        event_source=payload.eventSource,
        conditions=payload.conditionsJson,
        metadata=payload.metadata,
    )
    return ok(_s_trigger(obj))


@router.delete("/triggers/{trigger_id}", response_model=None, summary="Delete trigger")
def delete_trigger(
    trigger_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    _triggers.delete_trigger(db, trigger_id)
    return ok({"deleted": True, "id": str(trigger_id)})


# =========================================================================== #
# ACTIONS — literal-prefix                                                    #
# =========================================================================== #


@router.get("/actions/{action_id}", response_model=None, summary="Get action")
def get_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    return ok(_s_action(_actions.get_action(db, action_id)))


@router.patch("/actions/{action_id}", response_model=None, summary="Update action")
def update_action(
    action_id: uuid.UUID,
    payload: WorkflowActionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:update")),
):
    obj = _actions.update_action(
        db,
        action_id,
        sequence=payload.sequence,
        action_type=payload.actionType,
        configuration=payload.configurationJson,
        enabled=payload.enabled,
        metadata=payload.metadata,
    )
    return ok(_s_action(obj))


@router.delete("/actions/{action_id}", response_model=None, summary="Delete action")
def delete_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    _actions.delete_action(db, action_id)
    return ok({"deleted": True, "id": str(action_id)})


# =========================================================================== #
# EXECUTIONS — literal-prefix                                                 #
# =========================================================================== #


@router.get("/executions/{execution_id}", response_model=None, summary="Get execution")
def get_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    return ok(_s_execution(_executions.get_execution(db, execution_id)))


@router.patch("/executions/{execution_id}", response_model=None, summary="Update execution")
def update_execution(
    execution_id: uuid.UUID,
    payload: WorkflowExecutionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:update")),
):
    obj = _executions.update_execution(
        db,
        execution_id,
        context=payload.contextJson,
        metadata=payload.metadata,
    )
    return ok(_s_execution(obj))


@router.delete("/executions/{execution_id}", response_model=None, summary="Delete execution")
def delete_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    _executions.delete_execution(db, execution_id)
    return ok({"deleted": True, "id": str(execution_id)})


@router.post(
    "/executions/{execution_id}/complete",
    response_model=None,
    summary="Complete execution",
)
def complete_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:execute")),
):
    return ok(_s_execution(_executions.complete_execution(db, execution_id)))


@router.post(
    "/executions/{execution_id}/fail",
    response_model=None,
    summary="Fail execution",
)
def fail_execution(
    execution_id: uuid.UUID,
    payload: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:execute")),
):
    return ok(
        _s_execution(
            _executions.fail_execution(
                db, execution_id, reason=payload.get("reason")
            )
        )
    )


@router.post(
    "/executions/{execution_id}/cancel",
    response_model=None,
    summary="Cancel execution",
)
def cancel_execution(
    execution_id: uuid.UUID,
    payload: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:execute")),
):
    return ok(
        _s_execution(
            _executions.cancel_execution(
                db, execution_id, reason=payload.get("reason")
            )
        )
    )


# =========================================================================== #
# EXECUTION STEPS                                                             #
# =========================================================================== #


@router.get(
    "/executions/{execution_id}/steps",
    response_model=None,
    summary="List steps for execution",
)
def list_execution_steps(
    execution_id: uuid.UUID,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500, alias="pageSize"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    # Validate execution exists (raises NotFoundError otherwise).
    _executions.get_execution(db, execution_id)
    items, total = _executions.list_steps(
        db,
        execution_id=execution_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return paginated([_s_step(s) for s in items], page, page_size, total)


@router.post(
    "/executions/{execution_id}/steps",
    status_code=201,
    response_model=None,
    summary="Create step",
)
def create_execution_step(
    execution_id: uuid.UUID,
    payload: WorkflowExecutionStepCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:execute")),
):
    step = _executions.create_step(
        db,
        execution_id=execution_id,
        action_id=payload.workflowActionId,
        status=payload.status,
        metadata=payload.metadata,
    )
    return ok(_s_step(step))


@router.get("/steps/{step_id}", response_model=None, summary="Get step")
def get_step(
    step_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    return ok(_s_step(_executions.get_step(db, step_id)))


@router.patch("/steps/{step_id}", response_model=None, summary="Update step (transition)")
def update_step(
    step_id: uuid.UUID,
    payload: WorkflowExecutionStepUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:execute")),
):
    if payload.status is None:
        # PATCH without a status target is a no-op transition; just return current.
        return ok(_s_step(_executions.get_step(db, step_id)))
    step = _executions.transition_step(
        db,
        step_id,
        payload.status,
        output=payload.outputJson,
        error_message=payload.errorMessage,
    )
    return ok(_s_step(step))


@router.delete("/steps/{step_id}", response_model=None, summary="Delete step")
def delete_step(
    step_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    _executions.delete_step(db, step_id)
    return ok({"deleted": True, "id": str(step_id)})


@router.post(
    "/steps/{step_id}/retry",
    response_model=None,
    summary="Retry a failed step",
)
def retry_step(
    step_id: uuid.UUID,
    payload: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:execute")),
):
    max_retries = int(payload.get("maxRetries", 3))
    return ok(
        _s_step(_executions.retry_step(db, step_id, max_retries=max_retries))
    )


# =========================================================================== #
# WORKFLOW DEFINITIONS — collection root                                      #
# =========================================================================== #


@router.get("", response_model=None, summary="List workflows")
def list_workflows(
    q: str | None = Query(None),
    trigger_type: str | None = Query(None, alias="triggerType"),
    enabled: bool | None = Query(None),
    organization_id: str | None = Query(None, alias="organizationId"),
    created_from: datetime | None = Query(None, alias="createdFrom"),
    created_to: datetime | None = Query(None, alias="createdTo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500, alias="pageSize"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    items, total = _defs.search_workflows(
        db,
        query=q,
        trigger_type=trigger_type,
        enabled=enabled,
        organization_id=organization_id,
        created_from=created_from,
        created_to=created_to,
        page=page,
        page_size=page_size,
    )
    return paginated([_s_definition(w) for w in items], page, page_size, total)


@router.post("", status_code=201, response_model=None, summary="Create workflow")
def create_workflow(
    payload: WorkflowDefinitionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:create")),
):
    wf = _defs.create_workflow(
        db,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.triggerType,
        enabled=payload.enabled,
        organization_id=payload.organizationId,
        version=payload.version,
        metadata=payload.metadata,
    )
    return ok(_s_definition(wf))


# =========================================================================== #
# WORKFLOW DEFINITION — /{workflow_id} routes (LAST among catch-all segments) #
# =========================================================================== #


@router.get("/{workflow_id}", response_model=None, summary="Get workflow")
def get_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    return ok(_s_definition(_defs.get_workflow(db, workflow_id)))


@router.patch("/{workflow_id}", response_model=None, summary="Update workflow")
def update_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowDefinitionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:update")),
):
    wf = _defs.update_workflow(
        db,
        workflow_id,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.triggerType,
        enabled=payload.enabled,
        version=payload.version,
        metadata=payload.metadata,
    )
    return ok(_s_definition(wf))


@router.delete("/{workflow_id}", response_model=None, summary="Delete workflow")
def delete_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    _defs.delete_workflow(db, workflow_id)
    return ok({"deleted": True, "id": str(workflow_id)})


@router.post("/{workflow_id}/enable", response_model=None, summary="Enable workflow")
def enable_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    return ok(_s_definition(_defs.enable_workflow(db, workflow_id)))


@router.post("/{workflow_id}/disable", response_model=None, summary="Disable workflow")
def disable_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:manage")),
):
    return ok(_s_definition(_defs.disable_workflow(db, workflow_id)))


# --------------------------------------------------------------------------- #
# Triggers nested under a workflow definition
# --------------------------------------------------------------------------- #


@router.get(
    "/{workflow_id}/triggers",
    response_model=None,
    summary="List triggers for a workflow",
)
def list_workflow_triggers(
    workflow_id: uuid.UUID,
    event_name: str | None = Query(None, alias="eventName"),
    event_source: str | None = Query(None, alias="eventSource"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500, alias="pageSize"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    _defs.get_workflow(db, workflow_id)
    items, total = _triggers.list_triggers(
        db,
        workflow_definition_id=workflow_id,
        event_name=event_name,
        event_source=event_source,
        page=page,
        page_size=page_size,
    )
    return paginated([_s_trigger(t) for t in items], page, page_size, total)


@router.post(
    "/{workflow_id}/triggers",
    status_code=201,
    response_model=None,
    summary="Create trigger",
)
def create_workflow_trigger(
    workflow_id: uuid.UUID,
    payload: WorkflowTriggerCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:create")),
):
    t = _triggers.create_trigger(
        db,
        workflow_definition_id=workflow_id,
        event_name=payload.eventName,
        event_source=payload.eventSource,
        conditions=payload.conditionsJson,
        metadata=payload.metadata,
    )
    return ok(_s_trigger(t))


# --------------------------------------------------------------------------- #
# Actions nested under a workflow definition
# --------------------------------------------------------------------------- #


@router.get(
    "/{workflow_id}/actions",
    response_model=None,
    summary="List actions for a workflow",
)
def list_workflow_actions(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    _defs.get_workflow(db, workflow_id)
    actions = _actions.repo.ordered_actions(db, workflow_id)
    return ok([_s_action(a) for a in actions])


@router.post(
    "/{workflow_id}/actions",
    status_code=201,
    response_model=None,
    summary="Create action",
)
def create_workflow_action(
    workflow_id: uuid.UUID,
    payload: WorkflowActionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:create")),
):
    a = _actions.create_action(
        db,
        workflow_definition_id=workflow_id,
        sequence=payload.sequence,
        action_type=payload.actionType,
        configuration=payload.configurationJson,
        enabled=payload.enabled,
        metadata=payload.metadata,
    )
    return ok(_s_action(a))


@router.post(
    "/{workflow_id}/actions/reorder",
    response_model=None,
    summary="Reorder actions",
)
def reorder_workflow_actions(
    workflow_id: uuid.UUID,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:update")),
):
    ordered = payload.get("orderedActionIds") or payload.get("ordered_action_ids") or []
    result = _actions.reorder_actions(db, workflow_id, list(ordered))
    return ok([_s_action(a) for a in result])


# --------------------------------------------------------------------------- #
# Executions nested under a workflow definition
# --------------------------------------------------------------------------- #


@router.get(
    "/{workflow_id}/executions",
    response_model=None,
    summary="List executions for a workflow",
)
def list_workflow_executions(
    workflow_id: uuid.UUID,
    status: str | None = Query(None),
    started_from: datetime | None = Query(None, alias="startedFrom"),
    started_to: datetime | None = Query(None, alias="startedTo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500, alias="pageSize"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:view")),
):
    _defs.get_workflow(db, workflow_id)
    items, total = _executions.list_executions(
        db,
        workflow_definition_id=workflow_id,
        status=status,
        started_from=started_from,
        started_to=started_to,
        page=page,
        page_size=page_size,
    )
    return paginated([_s_execution(e) for e in items], page, page_size, total)


@router.post(
    "/{workflow_id}/executions",
    status_code=201,
    response_model=None,
    summary="Start execution",
)
def start_workflow_execution(
    workflow_id: uuid.UUID,
    payload: WorkflowExecutionCreate | None = Body(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("workflow:execute")),
):
    trigger_event = payload.triggerEvent if payload else None
    context = payload.contextJson if payload else None
    metadata = payload.metadata if payload else None
    exe = _executions.start_execution(
        db,
        workflow_definition_id=workflow_id,
        trigger_event=trigger_event,
        context=context,
        metadata=metadata,
    )
    return ok(_s_execution(exe))
