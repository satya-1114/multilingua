"""Model, schema, enum, and RBAC tests for the workflow engine.

Phase 7.1 — DB foundation only. Uses a dedicated SQLite in-memory
engine; JSONB is swapped for JSON so the tables build.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import JSON, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.constants.workflow import (
    ACTION_TYPES,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_WEBHOOK,
    STEP_STATUSES,
    STEP_STATUS_COMPLETED,
    STEP_STATUS_PENDING,
    TRIGGER_TYPES,
    TRIGGER_TYPE_EVENT,
    TRIGGER_TYPE_MANUAL,
    WORKFLOW_STATUSES,
    WORKFLOW_STATUS_PENDING,
    WORKFLOW_STATUS_RUNNING,
)
from app.models.workflow import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTrigger,
)
from app.schemas.workflow import (
    WorkflowActionCreate,
    WorkflowActionDto,
    WorkflowDefinitionCreate,
    WorkflowDefinitionDto,
    WorkflowExecutionCreate,
    WorkflowExecutionDto,
    WorkflowExecutionStepCreate,
    WorkflowExecutionStepDto,
    WorkflowTriggerCreate,
    WorkflowTriggerDto,
)
from app.security.rbac import has_permission


# --------------------------------------------------------------------------- #
# Test engine
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def engine():
    from sqlalchemy.dialects.postgresql import JSONB

    tables = (
        WorkflowDefinition.__table__,
        WorkflowTrigger.__table__,
        WorkflowAction.__table__,
        WorkflowExecution.__table__,
        WorkflowExecutionStep.__table__,
    )
    for table in tables:
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
        # Strip FKs pointing at unrelated tables (organizations).
        keep_fks: set = set()
        table_names = {t.name for t in tables}
        for col in list(table.columns):
            new_fks = set()
            for fk in col.foreign_keys:
                target_table = fk.column.table.name
                if target_table in table_names:
                    new_fks.add(fk)
            col.foreign_keys = new_fks
        table.constraints = {
            c
            for c in table.constraints
            if c.__class__.__name__ != "ForeignKeyConstraint"
            or all(
                el.column.table.name in table_names for el in c.elements
            )
        }
        _ = keep_fks  # silence unused

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
# Enums
# --------------------------------------------------------------------------- #


def test_enum_membership():
    assert TRIGGER_TYPE_EVENT in TRIGGER_TYPES
    assert TRIGGER_TYPE_MANUAL in TRIGGER_TYPES
    assert len(TRIGGER_TYPES) == 3
    assert WORKFLOW_STATUS_PENDING in WORKFLOW_STATUSES
    assert WORKFLOW_STATUS_RUNNING in WORKFLOW_STATUSES
    assert len(WORKFLOW_STATUSES) == 5
    assert STEP_STATUS_PENDING in STEP_STATUSES
    assert STEP_STATUS_COMPLETED in STEP_STATUSES
    assert len(STEP_STATUSES) == 5
    assert ACTION_TYPE_NOTIFICATION in ACTION_TYPES
    assert ACTION_TYPE_WEBHOOK in ACTION_TYPES
    assert len(ACTION_TYPES) == 8


# --------------------------------------------------------------------------- #
# Schemas — validation
# --------------------------------------------------------------------------- #


def test_definition_rejects_bad_trigger_type():
    with pytest.raises(ValidationError):
        WorkflowDefinitionCreate(name="w", trigger_type="nonsense")


def test_definition_defaults():
    dto = WorkflowDefinitionCreate(name="Onboarding", trigger_type="event")
    assert dto.enabled is True
    assert dto.version == 1
    assert dto.metadata == {}


def test_action_rejects_zero_sequence():
    with pytest.raises(ValidationError):
        WorkflowActionCreate(
            workflow_definition_id=uuid.uuid4(),
            sequence=0,
            action_type="notification",
        )


def test_action_rejects_bad_action_type():
    with pytest.raises(ValidationError):
        WorkflowActionCreate(
            workflow_definition_id=uuid.uuid4(),
            sequence=1,
            action_type="teleport",
        )


def test_execution_rejects_bad_status():
    with pytest.raises(ValidationError):
        WorkflowExecutionCreate(
            workflow_definition_id=uuid.uuid4(), status="exploded"
        )


def test_execution_rejects_inverted_times():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        WorkflowExecutionCreate(
            workflow_definition_id=uuid.uuid4(),
            started_at=now,
            completed_at=now - timedelta(minutes=1),
        )


def test_step_rejects_negative_retry():
    with pytest.raises(ValidationError):
        WorkflowExecutionStepCreate(
            workflow_execution_id=uuid.uuid4(),
            workflow_action_id=uuid.uuid4(),
            retry_count=-1,
        )


def test_step_rejects_bad_status():
    with pytest.raises(ValidationError):
        WorkflowExecutionStepCreate(
            workflow_execution_id=uuid.uuid4(),
            workflow_action_id=uuid.uuid4(),
            status="exploded",
        )


def test_trigger_create_defaults():
    dto = WorkflowTriggerCreate(
        workflow_definition_id=uuid.uuid4(),
        event_name="volunteer.created",
    )
    assert dto.conditionsJson == {}
    assert dto.metadata == {}


# --------------------------------------------------------------------------- #
# Models — persistence & relationships
# --------------------------------------------------------------------------- #


def _make_definition(session, name: str = "wf") -> WorkflowDefinition:
    d = WorkflowDefinition(
        name=name,
        trigger_type="event",
        enabled=True,
        version=1,
        metadata_={},
    )
    session.add(d)
    session.commit()
    return d


def test_definition_persists(session):
    d = _make_definition(session, "Onboarding")
    fetched = session.get(WorkflowDefinition, d.id)
    assert fetched is not None
    assert fetched.name == "Onboarding"
    assert fetched.enabled is True


def test_definition_unique_name_per_org(session):
    org = uuid.uuid4()
    session.add(
        WorkflowDefinition(
            name="Dup", trigger_type="event", organization_id=org, metadata_={}
        )
    )
    session.commit()
    session.add(
        WorkflowDefinition(
            name="Dup", trigger_type="event", organization_id=org, metadata_={}
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_action_unique_sequence_per_definition(session):
    d = _make_definition(session, "SeqTest")
    session.add(
        WorkflowAction(
            workflow_definition_id=d.id,
            sequence=1,
            action_type="notification",
        )
    )
    session.commit()
    session.add(
        WorkflowAction(
            workflow_definition_id=d.id,
            sequence=1,
            action_type="webhook",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_full_relationship_chain(session):
    d = _make_definition(session, "FullChain")
    t = WorkflowTrigger(
        workflow_definition_id=d.id,
        event_name="disaster.created",
        event_source="disaster",
    )
    a = WorkflowAction(
        workflow_definition_id=d.id,
        sequence=1,
        action_type="notification",
        configuration_json={"channel": "email"},
    )
    session.add_all([t, a])
    session.commit()

    now = datetime.now(timezone.utc)
    exe = WorkflowExecution(
        workflow_definition_id=d.id,
        trigger_event="disaster.created",
        status="running",
        started_at=now,
        context_json={"disaster_id": str(uuid.uuid4())},
    )
    session.add(exe)
    session.commit()

    step = WorkflowExecutionStep(
        workflow_execution_id=exe.id,
        workflow_action_id=a.id,
        status="completed",
        started_at=now,
        completed_at=now + timedelta(seconds=2),
        retry_count=0,
        output_json={"sent": True},
    )
    session.add(step)
    session.commit()

    fetched_def = session.get(WorkflowDefinition, d.id)
    assert len(fetched_def.triggers) == 1
    assert len(fetched_def.actions) == 1
    assert len(fetched_def.executions) == 1
    assert fetched_def.executions[0].steps[0].status == "completed"


# --------------------------------------------------------------------------- #
# DTO serialization
# --------------------------------------------------------------------------- #


def test_definition_dto_from_dict():
    now = datetime.now(timezone.utc)
    dto = WorkflowDefinitionDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "name": "Wf",
            "trigger_type": "manual",
            "enabled": False,
            "version": 3,
            "metadata": {"x": 1},
        }
    )
    assert dto.triggerType == "manual"
    assert dto.enabled is False
    assert dto.metadata == {"x": 1}


def test_execution_dto_roundtrip():
    now = datetime.now(timezone.utc)
    dto = WorkflowExecutionDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "workflow_definition_id": uuid.uuid4(),
            "trigger_event": "evt",
            "status": "completed",
            "started_at": now,
            "completed_at": now + timedelta(seconds=1),
            "context_json": {"k": "v"},
            "metadata": {},
        }
    )
    assert dto.status == "completed"
    assert dto.contextJson == {"k": "v"}


def test_trigger_and_action_and_step_dto_roundtrip():
    now = datetime.now(timezone.utc)
    common = {"id": uuid.uuid4(), "createdAt": now, "updatedAt": now}
    t = WorkflowTriggerDto.model_validate(
        {
            **common,
            "workflow_definition_id": uuid.uuid4(),
            "event_name": "e",
            "event_source": "s",
            "conditions_json": {"a": 1},
            "metadata": {},
        }
    )
    assert t.eventName == "e"

    a = WorkflowActionDto.model_validate(
        {
            **common,
            "workflow_definition_id": uuid.uuid4(),
            "sequence": 2,
            "action_type": "webhook",
            "configuration_json": {"url": "https://x"},
            "enabled": True,
            "metadata": {},
        }
    )
    assert a.actionType == "webhook"
    assert a.sequence == 2

    s = WorkflowExecutionStepDto.model_validate(
        {
            **common,
            "workflow_execution_id": uuid.uuid4(),
            "workflow_action_id": uuid.uuid4(),
            "status": "failed",
            "retry_count": 2,
            "output_json": {},
            "error_message": "boom",
            "metadata": {},
        }
    )
    assert s.status == "failed"
    assert s.retryCount == 2
    assert s.errorMessage == "boom"


# --------------------------------------------------------------------------- #
# Indexes
# --------------------------------------------------------------------------- #


def test_expected_indexes_defined():
    def_idx = {i.name for i in WorkflowDefinition.__table__.indexes}
    assert {
        "ix_workflow_definitions_name",
        "ix_workflow_definitions_enabled",
    }.issubset(def_idx)

    trg_idx = {i.name for i in WorkflowTrigger.__table__.indexes}
    assert {
        "ix_workflow_triggers_event_name",
        "ix_workflow_triggers_event_source",
    }.issubset(trg_idx)

    act_idx = {i.name for i in WorkflowAction.__table__.indexes}
    assert "ix_workflow_actions_definition_sequence" in act_idx

    exe_idx = {i.name for i in WorkflowExecution.__table__.indexes}
    assert {
        "ix_workflow_executions_status",
        "ix_workflow_executions_started_at",
        "ix_workflow_executions_definition",
    }.issubset(exe_idx)

    step_idx = {i.name for i in WorkflowExecutionStep.__table__.indexes}
    assert {
        "ix_workflow_execution_steps_execution",
        "ix_workflow_execution_steps_status",
    }.issubset(step_idx)


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #


def test_rbac_grants():
    assert has_permission(["super_admin"], "workflow:manage")
    assert has_permission(["org_admin"], "workflow:manage")
    assert has_permission(["org_admin"], "workflow:execute")
    assert has_permission(["automation_admin"], "workflow:view")
    assert has_permission(["automation_admin"], "workflow:create")
    assert has_permission(["automation_admin"], "workflow:update")
    assert has_permission(["automation_admin"], "workflow:execute")
    assert has_permission(["automation_admin"], "workflow:manage")
    assert has_permission(["viewer"], "workflow:view")
    assert not has_permission(["viewer"], "workflow:create")
    assert not has_permission(["viewer"], "workflow:manage")
    assert not has_permission(["volunteer"], "workflow:view")
