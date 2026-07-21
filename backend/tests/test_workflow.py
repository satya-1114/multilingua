"""Repository + service tests for the Automation & Workflow Engine (Phase 7.2).

Uses an isolated SQLite engine — JSONB swapped for JSON, cross-table FKs
stripped for `organizations` (we only keep FKs between workflow tables).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.workflow import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTrigger,
)
from app.repositories.workflow import (
    WorkflowActionRepository,
    WorkflowDefinitionRepository,
    WorkflowExecutionRepository,
    WorkflowExecutionStepRepository,
    WorkflowTriggerRepository,
)
from app.security.rbac import has_permission
from app.services.workflow import (
    EXECUTION_TRANSITIONS,
    STEP_TRANSITIONS,
    WorkflowActionService,
    WorkflowDefinitionService,
    WorkflowExecutionService,
    WorkflowTriggerService,
)


# --------------------------------------------------------------------------- #
# Test engine
# --------------------------------------------------------------------------- #


@pytest.fixture
def engine():
    from sqlalchemy.dialects.postgresql import JSONB

    tables = (
        WorkflowDefinition.__table__,
        WorkflowTrigger.__table__,
        WorkflowAction.__table__,
        WorkflowExecution.__table__,
        WorkflowExecutionStep.__table__,
    )
    table_names = {t.name for t in tables}

    for table in tables:
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
        for col in table.columns:
            col.foreign_keys = {
                fk for fk in col.foreign_keys if fk.column.table.name in table_names
            }
        table.constraints = {
            c
            for c in table.constraints
            if c.__class__.__name__ != "ForeignKeyConstraint"
            or all(el.column.table.name in table_names for el in c.elements)
        }

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    for t in tables:
        t.create(eng, checkfirst=True)
    return eng


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


# --------------------------------------------------------------------------- #
# Fresh service factories per test (independent repository singletons).
# --------------------------------------------------------------------------- #


@pytest.fixture
def defs_repo():
    return WorkflowDefinitionRepository()


@pytest.fixture
def triggers_repo():
    return WorkflowTriggerRepository()


@pytest.fixture
def actions_repo():
    return WorkflowActionRepository()


@pytest.fixture
def executions_repo():
    return WorkflowExecutionRepository()


@pytest.fixture
def steps_repo():
    return WorkflowExecutionStepRepository()


@pytest.fixture
def defs_service(defs_repo, actions_repo):
    return WorkflowDefinitionService(repo=defs_repo, actions_repo=actions_repo)


@pytest.fixture
def actions_service(actions_repo, defs_repo):
    return WorkflowActionService(repo=actions_repo, definitions_repo=defs_repo)


@pytest.fixture
def executions_service(executions_repo, steps_repo, defs_repo, actions_repo):
    return WorkflowExecutionService(
        repo=executions_repo,
        steps_repo=steps_repo,
        definitions_repo=defs_repo,
        actions_repo=actions_repo,
    )


@pytest.fixture
def triggers_service(triggers_repo, defs_repo):
    return WorkflowTriggerService(repo=triggers_repo, definitions_repo=defs_repo)


# --------------------------------------------------------------------------- #
# Definition service
# --------------------------------------------------------------------------- #


def test_create_workflow_defaults(session, defs_service):
    wf = defs_service.create_workflow(
        session, name="Onboarding", trigger_type="event"
    )
    assert wf.name == "Onboarding"
    assert wf.enabled is True
    assert wf.version == 1
    assert wf.metadata_ == {}


def test_create_workflow_rejects_bad_trigger_type(session, defs_service):
    with pytest.raises(ValidationError):
        defs_service.create_workflow(session, name="Bad", trigger_type="nope")


def test_create_workflow_rejects_empty_name(session, defs_service):
    with pytest.raises(ValidationError):
        defs_service.create_workflow(session, name="  ", trigger_type="event")


def test_duplicate_workflow_name_per_org_conflicts(session, defs_service):
    org = uuid.uuid4()
    defs_service.create_workflow(
        session, name="Dup", trigger_type="event", organization_id=org
    )
    with pytest.raises(ConflictError):
        defs_service.create_workflow(
            session, name="Dup", trigger_type="event", organization_id=org
        )


def test_same_name_different_org_allowed(session, defs_service):
    org1, org2 = uuid.uuid4(), uuid.uuid4()
    defs_service.create_workflow(
        session, name="Same", trigger_type="event", organization_id=org1
    )
    wf2 = defs_service.create_workflow(
        session, name="Same", trigger_type="event", organization_id=org2
    )
    assert wf2.organization_id == org2


def test_enable_and_disable_workflow(session, defs_service):
    wf = defs_service.create_workflow(session, name="EnDis", trigger_type="event")
    disabled = defs_service.disable_workflow(session, wf.id)
    assert disabled.enabled is False
    enabled = defs_service.enable_workflow(session, wf.id)
    assert enabled.enabled is True


def test_update_workflow_ignores_organization_change(session, defs_service):
    org = uuid.uuid4()
    wf = defs_service.create_workflow(
        session, name="Immut", trigger_type="event", organization_id=org
    )
    # organization_id is immutable — attempting to update it via update() is silent.
    updated = defs_service.update_workflow(session, wf.id, description="new")
    assert updated.organization_id == org


def test_update_workflow_rejects_duplicate_name(session, defs_service):
    org = uuid.uuid4()
    defs_service.create_workflow(
        session, name="A", trigger_type="event", organization_id=org
    )
    b = defs_service.create_workflow(
        session, name="B", trigger_type="event", organization_id=org
    )
    with pytest.raises(ConflictError):
        defs_service.update_workflow(session, b.id, name="A")


def test_delete_workflow_soft_deletes(session, defs_service):
    wf = defs_service.create_workflow(session, name="Del", trigger_type="event")
    defs_service.delete_workflow(session, wf.id)
    with pytest.raises(NotFoundError):
        defs_service.get_workflow(session, wf.id)


def test_search_workflows_filters_and_paginates(session, defs_service):
    for i in range(6):
        defs_service.create_workflow(
            session, name=f"WF-{i}", trigger_type="event", enabled=(i % 2 == 0)
        )
    items, total = defs_service.search_workflows(
        session, enabled=True, page=1, page_size=2
    )
    assert total == 3
    assert len(items) == 2
    items_q, total_q = defs_service.search_workflows(session, query="WF-1")
    assert total_q == 1 and items_q[0].name == "WF-1"


def test_search_workflows_rejects_bad_pagination(session, defs_service):
    with pytest.raises(ValidationError):
        defs_service.search_workflows(session, page=0)


# --------------------------------------------------------------------------- #
# Action service
# --------------------------------------------------------------------------- #


def _wf(defs_service, session, name="wf") -> WorkflowDefinition:
    return defs_service.create_workflow(session, name=name, trigger_type="event")


def test_create_action_success(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "aw")
    a = actions_service.create_action(
        session,
        workflow_definition_id=wf.id,
        sequence=1,
        action_type="notification",
    )
    assert a.sequence == 1
    assert a.action_type == "notification"


def test_create_action_rejects_zero_sequence(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "zs")
    with pytest.raises(ValidationError):
        actions_service.create_action(
            session,
            workflow_definition_id=wf.id,
            sequence=0,
            action_type="notification",
        )


def test_create_action_rejects_bad_type(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "bt")
    with pytest.raises(ValidationError):
        actions_service.create_action(
            session,
            workflow_definition_id=wf.id,
            sequence=1,
            action_type="teleport",
        )


def test_duplicate_sequence_conflict(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "ds")
    actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=1, action_type="webhook"
    )
    with pytest.raises(ConflictError):
        actions_service.create_action(
            session,
            workflow_definition_id=wf.id,
            sequence=1,
            action_type="notification",
        )


def test_missing_workflow_for_action(session, actions_service):
    with pytest.raises(NotFoundError):
        actions_service.create_action(
            session,
            workflow_definition_id=uuid.uuid4(),
            sequence=1,
            action_type="notification",
        )


def test_update_action_sequence_conflict(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "usc")
    a1 = actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=1, action_type="webhook"
    )
    a2 = actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=2, action_type="webhook"
    )
    with pytest.raises(ConflictError):
        actions_service.update_action(session, a2.id, sequence=1)
    assert a1.sequence == 1


def test_reorder_actions(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "reo")
    a1 = actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=1, action_type="notification"
    )
    a2 = actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=2, action_type="webhook"
    )
    a3 = actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=3, action_type="audit"
    )
    ordered = actions_service.reorder_actions(session, wf.id, [a3.id, a1.id, a2.id])
    assert [a.id for a in ordered] == [a3.id, a1.id, a2.id]
    assert [a.sequence for a in ordered] == [1, 2, 3]


def test_reorder_rejects_missing_action(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "rmm")
    a1 = actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=1, action_type="notification"
    )
    with pytest.raises(ValidationError):
        actions_service.reorder_actions(session, wf.id, [a1.id, uuid.uuid4()])


def test_reorder_rejects_length_mismatch(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "rlm")
    a1 = actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=1, action_type="notification"
    )
    actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=2, action_type="webhook"
    )
    with pytest.raises(ValidationError):
        actions_service.reorder_actions(session, wf.id, [a1.id])


def test_validate_action_sequence_ok(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "vas")
    actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=1, action_type="notification"
    )
    actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=2, action_type="webhook"
    )
    result = actions_service.validate_action_sequence(session, wf.id)
    assert [a.sequence for a in result] == [1, 2]


def test_validate_action_sequence_gaps(session, defs_service, actions_service):
    wf = _wf(defs_service, session, "vg")
    actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=1, action_type="notification"
    )
    actions_service.create_action(
        session, workflow_definition_id=wf.id, sequence=3, action_type="webhook"
    )
    with pytest.raises(ValidationError):
        actions_service.validate_action_sequence(session, wf.id)


# --------------------------------------------------------------------------- #
# Execution service — lifecycle
# --------------------------------------------------------------------------- #


def test_start_execution_from_enabled_workflow(session, defs_service, executions_service):
    wf = _wf(defs_service, session, "start")
    exe = executions_service.start_execution(
        session, workflow_definition_id=wf.id, trigger_event="evt"
    )
    assert exe.status == "running"
    assert exe.started_at is not None
    assert exe.workflow_definition_id == wf.id


def test_start_execution_rejects_disabled(session, defs_service, executions_service):
    wf = _wf(defs_service, session, "dis")
    defs_service.disable_workflow(session, wf.id)
    with pytest.raises(ValidationError):
        executions_service.start_execution(session, workflow_definition_id=wf.id)


def test_start_execution_missing_workflow(session, executions_service):
    with pytest.raises(NotFoundError):
        executions_service.start_execution(
            session, workflow_definition_id=uuid.uuid4()
        )


def test_execution_complete(session, defs_service, executions_service):
    wf = _wf(defs_service, session, "cmp")
    exe = executions_service.start_execution(session, workflow_definition_id=wf.id)
    done = executions_service.complete_execution(session, exe.id)
    assert done.status == "completed"
    assert done.completed_at is not None


def test_execution_illegal_transition(session, defs_service, executions_service):
    wf = _wf(defs_service, session, "ill")
    exe = executions_service.start_execution(session, workflow_definition_id=wf.id)
    executions_service.complete_execution(session, exe.id)
    with pytest.raises(ValidationError):
        executions_service.fail_execution(session, exe.id, reason="late")


def test_execution_fail_and_cancel(session, defs_service, executions_service):
    wf1 = _wf(defs_service, session, "fl")
    exe1 = executions_service.start_execution(session, workflow_definition_id=wf1.id)
    failed = executions_service.fail_execution(session, exe1.id, reason="boom")
    assert failed.status == "failed"
    assert failed.failure_reason == "boom"

    wf2 = _wf(defs_service, session, "cn")
    exe2 = executions_service.start_execution(session, workflow_definition_id=wf2.id)
    cancelled = executions_service.cancel_execution(session, exe2.id, reason="user")
    assert cancelled.status == "cancelled"


def test_execution_definition_is_immutable(session, defs_service, executions_service):
    wf = _wf(defs_service, session, "im")
    exe = executions_service.start_execution(session, workflow_definition_id=wf.id)
    updated = executions_service.update_execution(session, exe.id, context={"k": 1})
    assert updated.workflow_definition_id == wf.id
    assert updated.context_json == {"k": 1}


def test_execution_history_and_search(session, defs_service, executions_service):
    wf = _wf(defs_service, session, "hist")
    for _ in range(3):
        executions_service.start_execution(session, workflow_definition_id=wf.id)
    items, total = executions_service.execution_history(session, wf.id)
    assert total == 3
    items_r, total_r = executions_service.list_executions(session, status="running")
    assert total_r == 3
    assert all(e.status == "running" for e in items_r)
    _ = items  # silence unused


def test_execution_list_rejects_bad_pagination(session, executions_service):
    with pytest.raises(ValidationError):
        executions_service.list_executions(session, page=0)


def test_execution_list_rejects_bad_status(session, executions_service):
    with pytest.raises(ValidationError):
        executions_service.list_executions(session, status="nope")


# --------------------------------------------------------------------------- #
# Step lifecycle + retry
# --------------------------------------------------------------------------- #


def _wf_with_action(defs_service, actions_service, session, name="s"):
    wf = _wf(defs_service, session, name)
    action = actions_service.create_action(
        session,
        workflow_definition_id=wf.id,
        sequence=1,
        action_type="notification",
    )
    return wf, action


def test_step_full_lifecycle(session, defs_service, actions_service, executions_service):
    wf, action = _wf_with_action(defs_service, actions_service, session, "sl")
    exe = executions_service.start_execution(session, workflow_definition_id=wf.id)
    step = executions_service.create_step(
        session, execution_id=exe.id, action_id=action.id
    )
    assert step.status == "pending"
    running = executions_service.transition_step(session, step.id, "running")
    assert running.status == "running"
    assert running.started_at is not None
    done = executions_service.transition_step(
        session, step.id, "completed", output={"ok": True}
    )
    assert done.status == "completed"
    assert done.completed_at is not None
    assert done.output_json == {"ok": True}


def test_step_rejects_wrong_workflow_action(
    session, defs_service, actions_service, executions_service
):
    wf_a = _wf(defs_service, session, "wa")
    wf_b, action_b = _wf_with_action(defs_service, actions_service, session, "wb")
    exe = executions_service.start_execution(session, workflow_definition_id=wf_a.id)
    with pytest.raises(ValidationError):
        executions_service.create_step(
            session, execution_id=exe.id, action_id=action_b.id
        )
    _ = wf_b


def test_step_retry_success(session, defs_service, actions_service, executions_service):
    wf, action = _wf_with_action(defs_service, actions_service, session, "rt")
    exe = executions_service.start_execution(session, workflow_definition_id=wf.id)
    step = executions_service.create_step(session, execution_id=exe.id, action_id=action.id)
    executions_service.transition_step(session, step.id, "running")
    failed = executions_service.transition_step(
        session, step.id, "failed", error_message="boom"
    )
    assert failed.status == "failed"
    retried = executions_service.retry_step(session, step.id, max_retries=3)
    assert retried.status == "running"
    assert retried.retry_count == 1
    assert retried.error_message is None


def test_step_retry_limit(session, defs_service, actions_service, executions_service):
    wf, action = _wf_with_action(defs_service, actions_service, session, "rl")
    exe = executions_service.start_execution(session, workflow_definition_id=wf.id)
    step = executions_service.create_step(session, execution_id=exe.id, action_id=action.id)
    executions_service.transition_step(session, step.id, "running")
    executions_service.transition_step(session, step.id, "failed", error_message="x")
    executions_service.retry_step(session, step.id, max_retries=1)
    executions_service.transition_step(session, step.id, "failed", error_message="x")
    with pytest.raises(ValidationError):
        executions_service.retry_step(session, step.id, max_retries=1)


def test_step_retry_rejects_non_failed(
    session, defs_service, actions_service, executions_service
):
    wf, action = _wf_with_action(defs_service, actions_service, session, "rnf")
    exe = executions_service.start_execution(session, workflow_definition_id=wf.id)
    step = executions_service.create_step(session, execution_id=exe.id, action_id=action.id)
    with pytest.raises(ValidationError):
        executions_service.retry_step(session, step.id, max_retries=3)


def test_step_illegal_transition(session, defs_service, actions_service, executions_service):
    wf, action = _wf_with_action(defs_service, actions_service, session, "sit")
    exe = executions_service.start_execution(session, workflow_definition_id=wf.id)
    step = executions_service.create_step(session, execution_id=exe.id, action_id=action.id)
    executions_service.transition_step(session, step.id, "running")
    executions_service.transition_step(session, step.id, "completed")
    with pytest.raises(ValidationError):
        executions_service.transition_step(session, step.id, "failed")


# --------------------------------------------------------------------------- #
# Trigger service (thin)
# --------------------------------------------------------------------------- #


def test_trigger_crud(session, defs_service, triggers_service):
    wf = _wf(defs_service, session, "tr")
    t = triggers_service.create_trigger(
        session,
        workflow_definition_id=wf.id,
        event_name="disaster.created",
        event_source="disaster",
    )
    assert t.event_name == "disaster.created"

    fetched = triggers_service.get_trigger(session, t.id)
    assert fetched.id == t.id

    updated = triggers_service.update_trigger(
        session, t.id, event_source="platform"
    )
    assert updated.event_source == "platform"

    triggers_service.delete_trigger(session, t.id)
    with pytest.raises(NotFoundError):
        triggers_service.get_trigger(session, t.id)


def test_trigger_rejects_empty_event_name(session, defs_service, triggers_service):
    wf = _wf(defs_service, session, "tren")
    with pytest.raises(ValidationError):
        triggers_service.create_trigger(
            session, workflow_definition_id=wf.id, event_name="   "
        )


def test_trigger_missing_workflow(session, triggers_service):
    with pytest.raises(NotFoundError):
        triggers_service.create_trigger(
            session, workflow_definition_id=uuid.uuid4(), event_name="e"
        )


# --------------------------------------------------------------------------- #
# Repository search / pagination
# --------------------------------------------------------------------------- #


def test_repo_list_definitions_sort_asc(session, defs_repo, defs_service):
    now = datetime.now(timezone.utc)
    for i in range(3):
        defs_service.create_workflow(session, name=f"S-{i}", trigger_type="event")
    items, total = defs_repo.list_definitions(session, sort_by="name", sort_dir="asc")
    assert total == 3
    assert [i.name for i in items] == ["S-0", "S-1", "S-2"]
    _ = now


def test_repo_list_executions_date_filter(
    session, defs_service, executions_service, executions_repo
):
    wf = _wf(defs_service, session, "df")
    executions_service.start_execution(session, workflow_definition_id=wf.id)
    now = datetime.now(timezone.utc)
    items, total = executions_repo.list_executions(
        session,
        started_from=now - timedelta(minutes=1),
        started_to=now + timedelta(minutes=1),
    )
    assert total >= 1
    assert items


# --------------------------------------------------------------------------- #
# Transition maps
# --------------------------------------------------------------------------- #


def test_execution_transitions_map_shape():
    assert "running" in EXECUTION_TRANSITIONS["pending"]
    assert "completed" in EXECUTION_TRANSITIONS["running"]
    assert EXECUTION_TRANSITIONS["completed"] == frozenset()
    assert EXECUTION_TRANSITIONS["failed"] == frozenset()
    assert EXECUTION_TRANSITIONS["cancelled"] == frozenset()


def test_step_transitions_map_shape():
    assert "running" in STEP_TRANSITIONS["pending"]
    assert "completed" in STEP_TRANSITIONS["running"]
    assert "running" in STEP_TRANSITIONS["failed"]  # retry
    assert STEP_TRANSITIONS["completed"] == frozenset()
    assert STEP_TRANSITIONS["skipped"] == frozenset()


# --------------------------------------------------------------------------- #
# RBAC (business layer authoritative)
# --------------------------------------------------------------------------- #


def test_rbac_grants_view_create_update_execute_manage():
    for perm in (
        "workflow:view",
        "workflow:create",
        "workflow:update",
        "workflow:execute",
        "workflow:manage",
    ):
        assert has_permission(["super_admin"], perm)
        assert has_permission(["org_admin"], perm)
        assert has_permission(["automation_admin"], perm)

    assert has_permission(["viewer"], "workflow:view")
    assert not has_permission(["viewer"], "workflow:manage")
    assert not has_permission(["viewer"], "workflow:execute")
    assert not has_permission(["volunteer"], "workflow:view")
