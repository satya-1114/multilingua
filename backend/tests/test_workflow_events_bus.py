"""Event bus + trigger dispatcher tests (Phase 8.2)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.workflow import ACTION_TYPE_NOTIFICATION
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
from app.runtime import ActionRegistry, WorkflowRuntimeExecutor, WorkflowRuntimeService
from app.runtime.action_handlers import NotificationHandler
from app.runtime.events import (
    WILDCARD,
    WorkflowEvent,
    WorkflowEventBus,
    WorkflowTriggerDispatcher,
    build_event,
    install_default_subscribers,
    publish_event,
    trigger_matches_event,
    uninstall_default_subscribers,
)
from app.services.workflow import (
    WorkflowActionService,
    WorkflowDefinitionService,
    WorkflowExecutionService,
    WorkflowTriggerService,
)


# --------------------------------------------------------------------------- #
# SQLite engine
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
# Service + runtime fixtures
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
def triggers_service(triggers_repo, defs_repo):
    return WorkflowTriggerService(repo=triggers_repo, definitions_repo=defs_repo)


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
def registry():
    reg = ActionRegistry()
    reg.register(ACTION_TYPE_NOTIFICATION, NotificationHandler())
    return reg


@pytest.fixture
def runtime_service(
    registry, executions_service, defs_repo, actions_repo
):
    executor = WorkflowRuntimeExecutor(
        registry=registry,
        execution_service=executions_service,
        definitions_repo=defs_repo,
        actions_repo=actions_repo,
    )
    return WorkflowRuntimeService(registry=registry, executor=executor)


@pytest.fixture
def dispatcher(runtime_service, defs_repo, triggers_repo):
    return WorkflowTriggerDispatcher(
        runtime_service=runtime_service,
        definitions_repo=defs_repo,
        triggers_repo=triggers_repo,
    )


@pytest.fixture
def bus():
    return WorkflowEventBus()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_workflow(
    defs_service,
    actions_service,
    session,
    *,
    enabled: bool = True,
    org_id: uuid.UUID | None = None,
) -> WorkflowDefinition:
    wf = defs_service.create_workflow(
        session,
        name=f"wf-{uuid.uuid4().hex[:8]}",
        trigger_type="event",
        organization_id=org_id,
    )
    actions_service.create_action(
        session,
        workflow_definition_id=wf.id,
        sequence=1,
        action_type=ACTION_TYPE_NOTIFICATION,
        configuration={"title": "t", "message": "m", "user_id": "u"},
    )
    if not enabled:
        defs_service.disable_workflow(session, wf.id)
    return wf


def _make_trigger(triggers_service, session, wf, *, event_name, conditions=None):
    return triggers_service.create_trigger(
        session,
        workflow_definition_id=wf.id,
        event_name=event_name,
        conditions=conditions or {},
    )


# --------------------------------------------------------------------------- #
# WorkflowEvent
# --------------------------------------------------------------------------- #


def test_event_defaults_populated():
    ev = WorkflowEvent(event_type="foo.bar")
    assert ev.event_type == "foo.bar"
    assert ev.payload == {}
    assert ev.metadata == {}
    assert ev.timestamp.tzinfo is not None
    assert len(ev.correlation_id) == 32


def test_event_rejects_empty_type():
    with pytest.raises(ValueError):
        WorkflowEvent(event_type="")


def test_event_is_frozen():
    ev = WorkflowEvent(event_type="x")
    with pytest.raises(Exception):
        ev.event_type = "y"  # type: ignore[misc]


def test_event_to_dict():
    ev = WorkflowEvent(
        event_type="x",
        organization_id="org",
        actor_id="u",
        payload={"k": 1},
    )
    d = ev.to_dict()
    assert d["eventType"] == "x"
    assert d["organizationId"] == "org"
    assert d["actorId"] == "u"
    assert d["payload"] == {"k": 1}
    assert "timestamp" in d
    assert "correlationId" in d


def test_event_with_metadata_returns_copy():
    ev = WorkflowEvent(event_type="x", metadata={"a": 1})
    ev2 = ev.with_metadata(b=2)
    assert ev is not ev2
    assert ev2.metadata == {"a": 1, "b": 2}
    assert ev.metadata == {"a": 1}


def test_build_event_helper_coerces_uuids():
    org = uuid.uuid4()
    ev = build_event("x", organization_id=org, resource_id=org)
    assert ev.organization_id == str(org)
    assert ev.resource_id == str(org)


def test_build_event_preserves_correlation_id():
    ev = build_event("x", correlation_id="abc")
    assert ev.correlation_id == "abc"


# --------------------------------------------------------------------------- #
# EventBus
# --------------------------------------------------------------------------- #


def test_bus_subscribe_and_list(bus):
    def sub(event, ctx):  # noqa: ANN001
        pass

    bus.subscribe("x.y", sub)
    assert bus.list_subscribers("x.y") == {"x.y": ["sub"]}


def test_bus_subscribe_rejects_empty(bus):
    with pytest.raises(ValueError):
        bus.subscribe("", lambda e, c: None)


def test_bus_subscribe_rejects_non_callable(bus):
    with pytest.raises(TypeError):
        bus.subscribe("x", 42)  # type: ignore[arg-type]


def test_bus_publish_delivers(bus):
    calls: list = []

    def sub(event, ctx):
        calls.append((event.event_type, ctx.get("db")))

    bus.subscribe("x.y", sub)
    ev = WorkflowEvent(event_type="x.y")
    result = bus.publish(ev, context={"db": "session-marker"})
    assert calls == [("x.y", "session-marker")]
    assert len(result) == 1 and result[0]["ok"] is True


def test_bus_publish_no_subscribers_returns_empty(bus):
    ev = WorkflowEvent(event_type="unrelated")
    assert bus.publish(ev) == []


def test_bus_isolates_subscriber_failure(bus):
    def boom(event, ctx):
        raise RuntimeError("nope")

    good_calls: list = []

    def good(event, ctx):
        good_calls.append(event)

    bus.subscribe("x", boom)
    bus.subscribe("x", good)
    results = bus.publish(WorkflowEvent(event_type="x"))
    assert len(good_calls) == 1
    assert any(r["ok"] is False and r["error"] == "nope" for r in results)


def test_bus_wildcard_receives_every_event(bus):
    events: list[str] = []

    def wild(event, ctx):
        events.append(event.event_type)

    bus.subscribe(WILDCARD, wild)
    bus.publish(WorkflowEvent(event_type="a"))
    bus.publish(WorkflowEvent(event_type="b"))
    assert events == ["a", "b"]


def test_bus_unsubscribe(bus):
    calls: list = []
    sub = lambda e, c: calls.append(1)  # noqa: E731
    bus.subscribe("x", sub)
    assert bus.unsubscribe("x", sub) is True
    bus.publish(WorkflowEvent(event_type="x"))
    assert calls == []


def test_bus_unsubscribe_missing_returns_false(bus):
    assert bus.unsubscribe("x", lambda e, c: None) is False


def test_bus_clear(bus):
    bus.subscribe("x", lambda e, c: None)
    bus.clear()
    assert bus.list_subscribers() == {}


def test_bus_list_all_subscribers(bus):
    bus.subscribe("a", lambda e, c: None, name="sub_a")
    bus.subscribe("b", lambda e, c: None, name="sub_b")
    listing = bus.list_subscribers()
    assert set(listing.keys()) == {"a", "b"}
    assert listing["a"] == ["sub_a"]


def test_bus_dispatch_returns_diagnostics(bus):
    bus.subscribe("x", lambda e, c: None, name="ok")
    diag = bus.dispatch(WorkflowEvent(event_type="x"))
    assert diag[0]["subscriber"] == "ok"
    assert "duration" in diag[0]


def test_bus_wildcard_and_specific_both_fire(bus):
    hits: list[str] = []
    bus.subscribe(WILDCARD, lambda e, c: hits.append(f"w:{e.event_type}"))
    bus.subscribe("x", lambda e, c: hits.append(f"s:{e.event_type}"))
    bus.publish(WorkflowEvent(event_type="x"))
    assert set(hits) == {"w:x", "s:x"}


# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #


def _trigger(event_name="e.x", event_source=None, conditions=None):
    return WorkflowTrigger(
        id=uuid.uuid4(),
        workflow_definition_id=uuid.uuid4(),
        event_name=event_name,
        event_source=event_source,
        conditions_json=conditions or {},
        metadata_={},
    )


def test_filter_event_name_mismatch():
    assert (
        trigger_matches_event(_trigger("e.a"), WorkflowEvent(event_type="e.b"))
        is False
    )


def test_filter_event_name_match():
    assert trigger_matches_event(_trigger("e.a"), WorkflowEvent(event_type="e.a"))


def test_filter_event_source_check():
    t = _trigger(event_source="volunteer")
    assert (
        trigger_matches_event(t, WorkflowEvent(event_type="e.x", resource_type="task"))
        is False
    )
    assert trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", resource_type="volunteer")
    )


def test_filter_organization_scope():
    t = _trigger(conditions={"organization_id": "orgA"})
    assert trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", organization_id="orgA")
    )
    assert not trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", organization_id="orgB")
    )


def test_filter_resource_type_condition():
    t = _trigger(conditions={"resource_type": "volunteer"})
    assert trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", resource_type="volunteer")
    )
    assert not trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", resource_type="disaster")
    )


def test_filter_actor_condition():
    t = _trigger(conditions={"actor_id": "u1"})
    assert trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", actor_id="u1")
    )
    assert not trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", actor_id="u2")
    )


def test_filter_payload_exact_match():
    t = _trigger(conditions={"payload": {"severity": "high"}})
    assert trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", payload={"severity": "high"})
    )
    assert not trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", payload={"severity": "low"})
    )


def test_filter_payload_in_match():
    t = _trigger(conditions={"payload_in": {"status": ["a", "b"]}})
    assert trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", payload={"status": "a"})
    )
    assert not trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", payload={"status": "z"})
    )


def test_filter_metadata_match():
    t = _trigger(conditions={"metadata": {"channel": "sms"}})
    assert trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", metadata={"channel": "sms"})
    )
    assert not trigger_matches_event(
        t, WorkflowEvent(event_type="e.x", metadata={"channel": "email"})
    )


def test_filter_no_conditions_matches():
    t = _trigger()
    assert trigger_matches_event(t, WorkflowEvent(event_type="e.x"))


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #


def test_dispatch_no_matching_triggers(
    session, dispatcher, defs_service, actions_service, triggers_service
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="a")
    ev = WorkflowEvent(event_type="unrelated")
    result = dispatcher.dispatch(ev, {"db": session, "dry_run": True})
    assert result == []


def test_dispatch_launches_matching_workflow(
    session, dispatcher, defs_service, actions_service, triggers_service
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="v.created")
    ev = WorkflowEvent(event_type="v.created")
    result = dispatcher.dispatch(ev, {"db": session, "dry_run": True})
    assert len(result) == 1
    assert result[0]["launched"] is True
    assert result[0]["status"] == "completed"


def test_dispatch_multiple_matches(
    session, dispatcher, defs_service, actions_service, triggers_service
):
    wf1 = _make_workflow(defs_service, actions_service, session)
    wf2 = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf1, event_name="fanout")
    _make_trigger(triggers_service, session, wf2, event_name="fanout")
    result = dispatcher.dispatch(WorkflowEvent(event_type="fanout"), {"db": session, "dry_run": True})
    launched = [r for r in result if r["launched"]]
    assert len(launched) == 2


def test_dispatch_skips_disabled_workflow(
    session, dispatcher, defs_service, actions_service, triggers_service
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="dis.x")
    defs_service.disable_workflow(session, wf.id)
    result = dispatcher.dispatch(WorkflowEvent(event_type="dis.x"), {"db": session, "dry_run": True})
    assert len(result) == 1
    assert result[0]["launched"] is False
    assert result[0]["reason"] == "workflow_disabled"


def test_dispatch_respects_organization_filter(
    session, dispatcher, defs_service, actions_service, triggers_service
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(
        triggers_service,
        session,
        wf,
        event_name="scoped",
        conditions={"organization_id": "orgA"},
    )
    result = dispatcher.dispatch(
        WorkflowEvent(event_type="scoped", organization_id="orgB"),
        {"db": session, "dry_run": True},
    )
    assert result == []
    result = dispatcher.dispatch(
        WorkflowEvent(event_type="scoped", organization_id="orgA"),
        {"db": session, "dry_run": True},
    )
    assert result and result[0]["launched"]


def test_dispatch_respects_payload_filter(
    session, dispatcher, defs_service, actions_service, triggers_service
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(
        triggers_service,
        session,
        wf,
        event_name="p.check",
        conditions={"payload": {"severity": "critical"}},
    )
    assert (
        dispatcher.dispatch(
            WorkflowEvent(event_type="p.check", payload={"severity": "low"}),
            {"db": session, "dry_run": True},
        )
        == []
    )
    result = dispatcher.dispatch(
        WorkflowEvent(event_type="p.check", payload={"severity": "critical"}),
        {"db": session, "dry_run": True},
    )
    assert result and result[0]["launched"] is True


def test_dispatch_without_db_returns_empty(dispatcher):
    result = dispatcher.dispatch(WorkflowEvent(event_type="x"), {})
    assert result == []


def test_dispatch_unknown_event_no_op(
    session, dispatcher, defs_service, actions_service, triggers_service
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="known")
    assert dispatcher.dispatch(WorkflowEvent(event_type="never"), {"db": session, "dry_run": True}) == []


def test_dispatch_isolates_runtime_errors(
    session, dispatcher, defs_service, actions_service, triggers_service,
    runtime_service,
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="explode")

    def kaboom(*a, **kw):
        raise RuntimeError("runtime dead")

    runtime_service.execute_workflow = kaboom  # type: ignore[assignment]
    result = dispatcher.dispatch(WorkflowEvent(event_type="explode"), {"db": session, "dry_run": True})
    assert result[0]["launched"] is False
    assert "runtime dead" in result[0]["error"]


def test_dispatcher_is_callable(
    session, dispatcher, defs_service, actions_service, triggers_service
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="callable.x")
    # __call__ returns None but must not raise.
    dispatcher(WorkflowEvent(event_type="callable.x"), {"db": session, "dry_run": True})


# --------------------------------------------------------------------------- #
# End-to-end via bus + dispatcher
# --------------------------------------------------------------------------- #


def test_bus_dispatcher_end_to_end(
    session, bus, dispatcher, defs_service, actions_service, triggers_service
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="end.to.end")
    bus.subscribe(WILDCARD, dispatcher, name="dispatcher")
    bus.publish(WorkflowEvent(event_type="end.to.end"), context={"db": session, "dry_run": True})
    # If we got here without raising, execution ran; verify via runtime state.
    from app.repositories.workflow import workflow_executions
    _, total = workflow_executions.list_executions(
        session, workflow_definition_id=wf.id
    )
    assert total == 1


def test_publish_event_helper_uses_default_bus(monkeypatch):
    captured: list[WorkflowEvent] = []

    from app.runtime.events import bus as bus_module

    def fake_publish(event, *, context=None):
        captured.append(event)
        return []

    monkeypatch.setattr(bus_module.default_event_bus, "publish", fake_publish)
    publish_event("x.y", payload={"a": 1})
    assert captured and captured[0].event_type == "x.y"
    assert captured[0].payload == {"a": 1}


def test_install_default_subscribers_is_idempotent():

    b = WorkflowEventBus()
    assert install_default_subscribers(b) is True
    assert install_default_subscribers(b) is False
    uninstall_default_subscribers(b)


def test_install_default_subscribers_installs_wildcard():
    b = WorkflowEventBus()
    install_default_subscribers(b)
    listing = b.list_subscribers(WILDCARD)
    assert "WorkflowTriggerDispatcher" in listing[WILDCARD]
    uninstall_default_subscribers(b)


def test_uninstall_default_subscribers_removes_flag():
    b = WorkflowEventBus()
    install_default_subscribers(b)
    uninstall_default_subscribers(b)
    assert install_default_subscribers(b) is True
    uninstall_default_subscribers(b)


def test_dispatcher_metadata_contains_correlation_id(
    session, dispatcher, defs_service, actions_service, triggers_service,
    executions_repo,
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="meta.chk")
    ev = WorkflowEvent(event_type="meta.chk", correlation_id="corr-xyz")
    dispatcher.dispatch(ev, {"db": session, "dry_run": True})
    executions, _ = executions_repo.list_executions(
        session, workflow_definition_id=wf.id
    )
    assert executions[0].metadata_["correlationId"] == "corr-xyz"


def test_dispatcher_forwards_payload(
    session, dispatcher, defs_service, actions_service, triggers_service,
    executions_repo,
):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, event_name="pl.chk")
    dispatcher.dispatch(
        WorkflowEvent(event_type="pl.chk", payload={"k": "v"}),
        {"db": session, "dry_run": True},
    )
    executions, _ = executions_repo.list_executions(
        session, workflow_definition_id=wf.id
    )
    assert executions[0].context_json == {"k": "v"}


def test_event_timestamp_utc():
    ev = WorkflowEvent(event_type="x")
    assert ev.timestamp.utcoffset() == (datetime.now(timezone.utc)).utcoffset()


def test_bus_multiple_subscribers_all_fire(bus):
    counters = [0, 0, 0]

    def make(i):
        def sub(e, c):
            counters[i] += 1
        sub.__name__ = f"sub_{i}"
        return sub

    for i in range(3):
        bus.subscribe("multi", make(i))
    bus.publish(WorkflowEvent(event_type="multi"))
    assert counters == [1, 1, 1]


def test_bus_publish_returns_ok_flag_per_subscriber(bus):
    bus.subscribe("x", lambda e, c: None, name="a")
    bus.subscribe("x", lambda e, c: (_ for _ in ()).throw(ValueError("no")), name="b")
    res = bus.publish(WorkflowEvent(event_type="x"))
    okmap = {r["subscriber"]: r["ok"] for r in res}
    assert okmap == {"a": True, "b": False}
