"""Phase 7.4 — Workflow integration tests.

Verifies:
* audit events emitted for CRUD + lifecycle + retry
* notifications emitted for enable/disable/start/complete/fail
* search scope registered and returns hits
* analytics events emitted for create/execute/complete/fail/retry
* failure isolation: notification/audit/analytics blow-ups never
  abort the workflow operation, nor roll back caller state
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import JSON, create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.constants.analytics import METRIC_SCOPE_PLATFORM
from app.models.analytics import AnalyticsMetric
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.workflow import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTrigger,
)
from app.integrations import workflow_events
from app.services import search as search_svc


# --------------------------------------------------------------------------- #
# Isolated SQLite engine — strip cross-module FKs, JSONB → JSON.
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
        AuditLog.__table__,
        Notification.__table__,
        AnalyticsMetric.__table__,
    )
    keep = {t.name for t in tables}

    for table in tables:
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            column.foreign_keys = {
                fk for fk in column.foreign_keys if fk.column.table.name in keep
            }
        table.constraints = {
            c
            for c in table.constraints
            if c.__class__.__name__ != "ForeignKeyConstraint"
            or all(el.column.table.name in keep for el in c.elements)
        }

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
        s.close()


# --------------------------------------------------------------------------- #
# Model factories
# --------------------------------------------------------------------------- #


def _wf(session, **over) -> WorkflowDefinition:
    wf = WorkflowDefinition(
        name=over.get("name", f"wf-{uuid.uuid4().hex[:6]}"),
        description=over.get("description", "test workflow"),
        trigger_type=over.get("trigger_type", "manual"),
        enabled=over.get("enabled", True),
        organization_id=None,
        version=1,
        metadata_={},
    )
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


def _exec(session, wf: WorkflowDefinition, **over) -> WorkflowExecution:
    exe = WorkflowExecution(
        workflow_definition_id=wf.id,
        trigger_event=over.get("trigger_event", "manual"),
        status=over.get("status", "running"),
        context_json={},
        metadata_={},
    )
    session.add(exe)
    session.commit()
    session.refresh(exe)
    return exe


def _action(session, wf: WorkflowDefinition, sequence: int = 1) -> WorkflowAction:
    a = WorkflowAction(
        workflow_definition_id=wf.id,
        action_type="custom",
        sequence=sequence,
        configuration_json={},
        metadata_={},
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _step(session, exe: WorkflowExecution, action: WorkflowAction, **over) -> WorkflowExecutionStep:
    step = WorkflowExecutionStep(
        workflow_execution_id=exe.id,
        workflow_action_id=action.id,
        status=over.get("status", "failed"),
        retry_count=over.get("retry_count", 1),
        metadata_={},
    )
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def _audits(session, module: str | None = None) -> list[AuditLog]:
    rows = list(session.scalars(select(AuditLog)))
    return [a for a in rows if module is None or a.module == module]


def _notifs(session) -> list[Notification]:
    return list(session.scalars(select(Notification)))


def _metrics(session) -> list[AnalyticsMetric]:
    return list(session.scalars(select(AnalyticsMetric)))


# --------------------------------------------------------------------------- #
# Audit integration
# --------------------------------------------------------------------------- #


def test_workflow_created_writes_audit_and_metric(session):
    wf = _wf(session)
    workflow_events.workflow_created(session, wf, actor_id=uuid.uuid4())

    audit = _audits(session, workflow_events.MODULE_DEFINITION)
    assert any(a.action == "create" and a.entity_id == str(wf.id) for a in audit)

    m = _metrics(session)
    assert any(
        x.metric_name == "workflow.created"
        and x.metric_scope == METRIC_SCOPE_PLATFORM
        and x.entity_type == "workflow_definition"
        for x in m
    )


def test_workflow_update_delete_audited(session):
    wf = _wf(session)
    workflow_events.workflow_updated(session, wf, changes={"name": "x"})
    workflow_events.workflow_deleted(session, wf)
    actions = {a.action for a in _audits(session, workflow_events.MODULE_DEFINITION)}
    assert {"update", "delete"}.issubset(actions)


def test_execution_lifecycle_audited(session):
    wf = _wf(session)
    exe = _exec(session, wf)
    workflow_events.execution_started(session, exe)
    workflow_events.execution_completed(session, exe)
    workflow_events.execution_failed(session, exe, reason="boom")
    workflow_events.execution_cancelled(session, exe, reason="stop")

    actions = {a.action for a in _audits(session, workflow_events.MODULE_EXECUTION)}
    assert {"start", "complete", "fail", "cancel"}.issubset(actions)

    fail = next(a for a in _audits(session, workflow_events.MODULE_EXECUTION) if a.action == "fail")
    assert (fail.metadata_ or {}).get("reason") == "boom"


def test_step_retry_audited(session):
    wf = _wf(session)
    exe = _exec(session, wf)
    step = _step(session, exe, _action(session, wf), retry_count=2)
    workflow_events.step_retried(session, step)

    audit = _audits(session, workflow_events.MODULE_STEP)
    assert any(a.action == "retry" and (a.metadata_ or {}).get("retry_count") == 2 for a in audit)


# --------------------------------------------------------------------------- #
# Notification integration
# --------------------------------------------------------------------------- #


def test_enable_disable_broadcasts_notifications(session):
    wf = _wf(session)
    actor = uuid.uuid4()
    workflow_events.workflow_enabled(session, wf, actor_id=actor)
    workflow_events.workflow_disabled(session, wf, actor_id=actor)
    titles = " ".join(n.title.lower() for n in _notifs(session))
    assert "enabled" in titles and "disabled" in titles
    assert all(n.category == workflow_events.CATEGORY for n in _notifs(session))


def test_execution_started_completed_failed_broadcast(session):
    wf = _wf(session)
    exe = _exec(session, wf)
    actor = uuid.uuid4()

    workflow_events.execution_started(session, exe, actor_id=actor)
    workflow_events.execution_completed(session, exe, actor_id=actor)
    workflow_events.execution_failed(session, exe, actor_id=actor, reason="oops")

    notifs = _notifs(session)
    titles = " ".join(n.title.lower() for n in notifs)
    assert "started" in titles and "completed" in titles and "failed" in titles
    assert any(n.priority == "high" and "failed" in n.title.lower() for n in notifs)


def test_broadcast_deduplicates_recipients(session):
    wf = _wf(session)
    actor = uuid.uuid4()
    workflow_events.workflow_enabled(
        session, wf, actor_id=actor, notify_user_ids=[actor, actor, None],
    )
    assert len(_notifs(session)) == 1


def test_broadcast_ignores_invalid_user_ids(session):
    wf = _wf(session)
    workflow_events.workflow_enabled(
        session, wf, actor_id="not-a-uuid", notify_user_ids=[None, "also-bad"],
    )
    assert _notifs(session) == []


# --------------------------------------------------------------------------- #
# Search integration
# --------------------------------------------------------------------------- #


def test_search_scope_registered():
    assert "workflow" in search_svc._HANDLERS
    assert search_svc.SCOPE_PERMISSIONS.get("workflow") == "workflow:view"


def test_search_returns_definition_and_execution_hits(session):
    wf = _wf(session, name="findable-alpha", trigger_type="manual")
    _exec(session, wf, trigger_event="findable-alpha")

    hits = search_svc._HANDLERS["workflow"](session, "findable-alpha", None, 20)
    scopes = {h["scope"] for h in hits}
    titles = " ".join(h["title"] for h in hits).lower()
    assert scopes == {"workflow"}
    assert "workflow" in titles and "execution" in titles


# --------------------------------------------------------------------------- #
# Analytics integration
# --------------------------------------------------------------------------- #


def test_analytics_metrics_recorded_for_lifecycle(session):
    wf = _wf(session)
    exe = _exec(session, wf)
    step = _step(session, exe, _action(session, wf), retry_count=1)

    workflow_events.workflow_created(session, wf)
    workflow_events.execution_started(session, exe)
    workflow_events.execution_completed(session, exe)
    workflow_events.execution_failed(session, exe, reason="x")
    workflow_events.step_retried(session, step)

    names = {m.metric_name for m in _metrics(session)}
    assert {
        "workflow.created",
        "workflow.executed",
        "workflow.completed",
        "workflow.failed",
        "workflow.retry",
    }.issubset(names)
    assert all(m.metric_scope == METRIC_SCOPE_PLATFORM for m in _metrics(session))


# --------------------------------------------------------------------------- #
# Failure isolation
# --------------------------------------------------------------------------- #


def test_notification_failure_isolated(session, monkeypatch):
    from app.services import notifications as notif_service

    monkeypatch.setattr(notif_service, "create",
                        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("notif down")))
    wf = _wf(session)
    # Must not raise even though notif backend is down.
    workflow_events.workflow_enabled(session, wf, actor_id=uuid.uuid4())


def test_audit_failure_isolated_and_workflow_state_preserved(session, monkeypatch):
    from app.services import audit as audit_service

    wf = _wf(session)
    wf_id = wf.id

    def boom(*a, **kw):
        raise RuntimeError("audit down")

    monkeypatch.setattr(audit_service, "log", boom)
    # Must not raise.
    workflow_events.workflow_updated(session, wf, changes={"name": "y"})

    # Caller state (the workflow row) is untouched.
    fresh = session.get(WorkflowDefinition, wf_id)
    assert fresh is not None and fresh.name == wf.name


def test_analytics_failure_isolated(session, monkeypatch):
    from app.services import analytics as analytics_service

    def boom(*a, **kw):
        raise RuntimeError("analytics down")

    monkeypatch.setattr(analytics_service.metric_service, "record_metric", boom)
    wf = _wf(session)
    exe = _exec(session, wf)
    # Every emitter that would record analytics must swallow the error.
    workflow_events.workflow_created(session, wf)
    workflow_events.execution_started(session, exe)
    workflow_events.execution_failed(session, exe, reason="x")
    step = _step(session, exe, _action(session, wf))
    workflow_events.step_retried(session, step)


def test_integration_failure_does_not_rollback_prior_writes(session, monkeypatch):
    from app.services import notifications as notif_service

    # Seed a committed workflow row before triggering the failure.
    wf = _wf(session, name="preserved")

    monkeypatch.setattr(notif_service, "create",
                        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("notif down")))
    workflow_events.workflow_enabled(session, wf, actor_id=uuid.uuid4())

    # The prior insert survives.
    assert session.get(WorkflowDefinition, wf.id) is not None
