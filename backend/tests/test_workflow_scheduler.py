"""Workflow scheduler / queue / Celery tests (Phase 8.3)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.workflow import (
    ACTION_TYPE_NOTIFICATION,
)
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
    WorkflowTriggerRepository,
)
from app.runtime import ActionRegistry, WorkflowRuntimeExecutor, WorkflowRuntimeService
from app.runtime.action_handlers import NotificationHandler
from app.runtime.scheduler import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF,
    CeleryWorkflowQueue,
    CronValidationError,
    EnqueueResult,
    InMemoryWorkflowQueue,
    ScheduledRun,
    WORKFLOW_QUEUES,
    WorkflowQueue,
    WorkflowScheduler,
    default_workflow_queue,
    execute_workflow_task,
    next_run_at,
    parse_cron,
    run_workflow_execution,
    set_default_workflow_queue,
    validate_cron,
    workflow_celery_app,
)
from app.runtime.scheduler.celery_app import (
    WORKFLOW_QUEUE_DEFAULT,
    WORKFLOW_QUEUE_MAIN,
    WORKFLOW_QUEUE_NOTIFICATIONS,
)
from app.runtime.scheduler.tasks import (
    NON_RETRYABLE_EXCEPTIONS,
    RETRYABLE_EXCEPTIONS,
    _compute_countdown,
)
from app.runtime.exceptions import (
    ActionExecutionError,
    InvalidWorkflowError,
    UnknownActionError,
)
from app.services.workflow import (
    WorkflowActionService,
    WorkflowDefinitionService,
    WorkflowTriggerService,
)


# --------------------------------------------------------------------------- #
# Engine / session
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


@pytest.fixture
def runtime_service():
    reg = ActionRegistry()
    reg.register(ACTION_TYPE_NOTIFICATION, NotificationHandler())
    executor = WorkflowRuntimeExecutor(registry=reg)
    return WorkflowRuntimeService(registry=reg, executor=executor)


@pytest.fixture
def defs_service():
    return WorkflowDefinitionService(
        repo=WorkflowDefinitionRepository(),
        actions_repo=WorkflowActionRepository(),
    )


@pytest.fixture
def actions_service():
    return WorkflowActionService(
        repo=WorkflowActionRepository(),
        definitions_repo=WorkflowDefinitionRepository(),
    )


@pytest.fixture
def triggers_service():
    return WorkflowTriggerService(
        repo=WorkflowTriggerRepository(),
        definitions_repo=WorkflowDefinitionRepository(),
    )


def _make_workflow(defs_service, actions_service, session, *, trigger_type="schedule"):
    wf = defs_service.create_workflow(
        session,
        name=f"wf-{uuid.uuid4().hex[:8]}",
        trigger_type=trigger_type,
    )
    actions_service.create_action(
        session,
        workflow_definition_id=wf.id,
        sequence=1,
        action_type=ACTION_TYPE_NOTIFICATION,
        configuration={"title": "t", "message": "m", "user_id": "u"},
    )
    return wf


def _make_trigger(triggers_service, session, wf, *, cron="*/5 * * * *"):
    return triggers_service.create_trigger(
        session,
        workflow_definition_id=wf.id,
        event_name="scheduled.run",
        conditions={"cron": cron},
    )


# --------------------------------------------------------------------------- #
# Celery app
# --------------------------------------------------------------------------- #


def test_celery_app_named_workflow():
    assert workflow_celery_app.main == "workflow"


def test_celery_app_registers_execute_task():
    assert "workflow.execute" in workflow_celery_app.tasks


def test_celery_queues_include_main_default_and_notifications():
    assert set(WORKFLOW_QUEUES) == {
        WORKFLOW_QUEUE_DEFAULT,
        WORKFLOW_QUEUE_MAIN,
        WORKFLOW_QUEUE_NOTIFICATIONS,
    }


def test_celery_default_queue_is_default():
    assert workflow_celery_app.conf.task_default_queue == WORKFLOW_QUEUE_DEFAULT


def test_celery_execute_task_routes_to_workflow_queue():
    routes = workflow_celery_app.conf.task_routes
    assert routes["workflow.execute"]["queue"] == WORKFLOW_QUEUE_MAIN


def test_celery_acks_late_and_reject_on_worker_lost():
    conf = workflow_celery_app.conf
    assert conf.task_acks_late is True
    assert conf.task_reject_on_worker_lost is True


def test_celery_time_limits_configured():
    conf = workflow_celery_app.conf
    assert conf.task_time_limit == 600
    assert conf.task_soft_time_limit == 540


def test_celery_task_object_bind_and_retries():
    task = workflow_celery_app.tasks["workflow.execute"]
    assert task.max_retries == DEFAULT_MAX_RETRIES
    assert task.acks_late is True


def test_celery_app_isolated_from_platform_app():
    from app.workers.celery_app import celery_app as platform_app

    assert workflow_celery_app is not platform_app
    assert workflow_celery_app.main != platform_app.main


# --------------------------------------------------------------------------- #
# Cron
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "expr",
    [
        "* * * * *",
        "*/5 * * * *",
        "0 0 * * *",
        "0 12 * * 1-5",
        "0 0 1 1 *",
        "30 6,18 * * *",
        "@daily",
        "@hourly",
        "@weekly",
        "@monthly",
        "@yearly",
    ],
)
def test_validate_cron_accepts_valid(expr):
    assert validate_cron(expr) is True


@pytest.mark.parametrize(
    "expr",
    [
        "",
        "   ",
        "not-a-cron",
        "* * *",
        "* * * *",
        "* * * * * *",
        "60 * * * *",
        "* 25 * * *",
        "* * 32 * *",
        "* * * 13 *",
        "* * * * 8",
    ],
)
def test_validate_cron_rejects_invalid(expr):
    assert validate_cron(expr) is False


def test_parse_cron_returns_crontab():
    from celery.schedules import crontab

    c = parse_cron("*/10 * * * *")
    assert isinstance(c, crontab)


def test_parse_cron_raises_typed_error():
    with pytest.raises(CronValidationError):
        parse_cron("bogus")


def test_parse_cron_rejects_non_string():
    with pytest.raises(CronValidationError):
        parse_cron(None)  # type: ignore[arg-type]


def test_parse_cron_alias_daily_equivalent():
    a = parse_cron("@daily")
    b = parse_cron("0 0 * * *")
    assert a.minute == b.minute and a.hour == b.hour


def test_next_run_at_is_utc_and_in_future():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    nxt = next_run_at("*/5 * * * *", now=now)
    assert nxt.tzinfo is not None
    assert nxt > now


def test_next_run_at_naive_now_is_treated_as_utc():
    naive = datetime(2026, 1, 1, 12, 0)
    nxt = next_run_at("*/5 * * * *", now=naive)
    assert nxt.tzinfo is not None


def test_next_run_at_hourly():
    now = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
    nxt = next_run_at("0 * * * *", now=now)
    assert nxt == datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc)


def test_next_run_at_invalid_expr_raises():
    with pytest.raises(CronValidationError):
        next_run_at("nope")


# --------------------------------------------------------------------------- #
# Queue abstraction
# --------------------------------------------------------------------------- #


def test_workflow_queue_is_abstract():
    with pytest.raises(TypeError):
        WorkflowQueue()  # type: ignore[abstract]


def test_in_memory_enqueue_records_task():
    q = InMemoryWorkflowQueue()
    wf_id = uuid.uuid4()
    result = q.enqueue(wf_id, payload={"k": 1}, trigger_event="manual")
    assert isinstance(result, EnqueueResult)
    assert result.workflow_id == str(wf_id)
    assert result.queue == WORKFLOW_QUEUE_MAIN
    assert result.scheduled_for is None
    assert q.tasks()[0].kwargs["payload"] == {"k": 1}


def test_in_memory_schedule_records_run_at():
    q = InMemoryWorkflowQueue()
    when = datetime.now(timezone.utc) + timedelta(minutes=5)
    result = q.schedule(uuid.uuid4(), run_at=when)
    assert result.scheduled_for == when
    assert result.eta_seconds is not None and result.eta_seconds > 0


def test_in_memory_schedule_naive_datetime_treated_as_utc():
    q = InMemoryWorkflowQueue()
    naive = datetime.utcnow() + timedelta(minutes=1)
    result = q.schedule(uuid.uuid4(), run_at=naive)
    assert result.scheduled_for is not None
    assert result.scheduled_for.tzinfo is not None


def test_in_memory_queue_defaults_to_main_queue():
    q = InMemoryWorkflowQueue()
    assert q.enqueue(uuid.uuid4()).queue == WORKFLOW_QUEUE_MAIN


def test_in_memory_queue_accepts_valid_named_queues():
    q = InMemoryWorkflowQueue()
    for name in WORKFLOW_QUEUES:
        assert q.enqueue(uuid.uuid4(), queue=name).queue == name


def test_in_memory_queue_rejects_unknown_queue():
    q = InMemoryWorkflowQueue()
    with pytest.raises(ValueError):
        q.enqueue(uuid.uuid4(), queue="nope")


def test_in_memory_queue_pop_ready_filters_future():
    q = InMemoryWorkflowQueue()
    q.enqueue(uuid.uuid4())
    q.schedule(uuid.uuid4(), run_at=datetime.now(timezone.utc) + timedelta(hours=1))
    ready = q.pop_ready()
    assert len(ready) == 1
    remaining = q.tasks()
    assert len(remaining) == 1 and remaining[0].run_at is not None


def test_in_memory_queue_clear():
    q = InMemoryWorkflowQueue()
    q.enqueue(uuid.uuid4())
    q.clear()
    assert q.tasks() == []


def test_in_memory_queue_records_task_id_uniqueness():
    q = InMemoryWorkflowQueue()
    ids = {q.enqueue(uuid.uuid4()).task_id for _ in range(5)}
    assert len(ids) == 5


def test_in_memory_queue_metadata_preserved():
    q = InMemoryWorkflowQueue()
    result = q.enqueue(uuid.uuid4(), metadata={"src": "test"})
    assert result.metadata == {"src": "test"}


def test_celery_queue_enqueue_calls_send_task():
    fake_app = MagicMock()
    fake_app.send_task.return_value = MagicMock(id="celery-task-123")
    q = CeleryWorkflowQueue(celery_app=fake_app)
    result = q.enqueue(uuid.uuid4(), payload={"a": 1})
    assert result.task_id == "celery-task-123"
    assert result.queue == WORKFLOW_QUEUE_MAIN
    fake_app.send_task.assert_called_once()
    _, kwargs = fake_app.send_task.call_args
    assert kwargs["queue"] == WORKFLOW_QUEUE_MAIN
    assert kwargs["kwargs"]["payload"] == {"a": 1}


def test_celery_queue_schedule_sends_eta():
    fake_app = MagicMock()
    fake_app.send_task.return_value = MagicMock(id="t")
    q = CeleryWorkflowQueue(celery_app=fake_app)
    when = datetime.now(timezone.utc) + timedelta(minutes=10)
    q.schedule(uuid.uuid4(), run_at=when)
    _, kwargs = fake_app.send_task.call_args
    assert kwargs["eta"].tzinfo is not None
    assert kwargs["eta"] == when


def test_celery_queue_rejects_unknown_queue():
    q = CeleryWorkflowQueue(celery_app=MagicMock())
    with pytest.raises(ValueError):
        q.enqueue(uuid.uuid4(), queue="bogus")


def test_celery_queue_task_name_constant():
    assert CeleryWorkflowQueue.task_name == "workflow.execute"


def test_default_workflow_queue_swappable():
    original = default_workflow_queue()
    swap = InMemoryWorkflowQueue()
    previous = set_default_workflow_queue(swap)
    try:
        assert default_workflow_queue() is swap
    finally:
        set_default_workflow_queue(previous)
    assert default_workflow_queue() is original


# --------------------------------------------------------------------------- #
# Runtime service enqueue integration
# --------------------------------------------------------------------------- #


def test_runtime_service_execute_sync_alias(runtime_service, defs_service,
                                            actions_service, session):
    wf = _make_workflow(defs_service, actions_service, session, trigger_type="manual")
    result = runtime_service.execute_sync(session, wf.id, metadata={"dry_run": True})
    assert result.success is True


def test_runtime_service_enqueue_execution_uses_default_queue():
    q = InMemoryWorkflowQueue()
    previous = set_default_workflow_queue(q)
    try:
        svc = WorkflowRuntimeService()
        wf_id = uuid.uuid4()
        result = svc.enqueue_execution(wf_id, payload={"x": 1})
        assert result.workflow_id == str(wf_id)
        assert q.tasks()[0].kwargs["payload"] == {"x": 1}
    finally:
        set_default_workflow_queue(previous)


def test_runtime_service_enqueue_execution_schedules_when_run_at_given():
    q = InMemoryWorkflowQueue()
    previous = set_default_workflow_queue(q)
    try:
        svc = WorkflowRuntimeService()
        when = datetime.now(timezone.utc) + timedelta(minutes=1)
        result = svc.enqueue_execution(uuid.uuid4(), run_at=when)
        assert result.scheduled_for is not None
    finally:
        set_default_workflow_queue(previous)


# --------------------------------------------------------------------------- #
# Scheduler
# --------------------------------------------------------------------------- #


def test_scheduler_discover_empty(session):
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    assert scheduler.discover(session) == []


def test_scheduler_discovers_schedule_trigger(session, defs_service,
                                              actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, cron="*/5 * * * *")
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    pairs = scheduler.discover(session)
    assert len(pairs) == 1 and pairs[0][0].id == wf.id


def test_scheduler_ignores_non_schedule_workflows(session, defs_service,
                                                  actions_service):
    _make_workflow(defs_service, actions_service, session, trigger_type="manual")
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    assert scheduler.discover(session) == []


def test_scheduler_ignores_triggers_without_cron(session, defs_service,
                                                 actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    triggers_service.create_trigger(
        session,
        workflow_definition_id=wf.id,
        event_name="scheduled.run",
        conditions={},
    )
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    assert scheduler.discover(session) == []


def test_scheduler_skips_disabled_workflows(session, defs_service,
                                            actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf)
    defs_service.disable_workflow(session, wf.id)
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    assert scheduler.discover(session) == []


def test_scheduler_filters_invalid_cron(session, defs_service,
                                        actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    triggers_service.create_trigger(
        session,
        workflow_definition_id=wf.id,
        event_name="scheduled.run",
        conditions={"cron": "not a cron"},
    )
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    assert scheduler.discover(session) == []


def test_scheduler_enqueue_due_fires_matching(session, defs_service,
                                              actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, cron="*/5 * * * *")
    q = InMemoryWorkflowQueue()
    scheduler = WorkflowScheduler(queue=q)
    now = datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc)
    runs = scheduler.enqueue_due(session, now=now, window=timedelta(minutes=10))
    assert len(runs) == 1
    assert runs[0].enqueued is True
    assert runs[0].enqueue_result is not None
    assert q.tasks(), "task should be recorded"


def test_scheduler_deduplicates_within_same_window(session, defs_service,
                                                   actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, cron="*/5 * * * *")
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    now = datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc)
    first = scheduler.enqueue_due(session, now=now, window=timedelta(minutes=10))
    second = scheduler.enqueue_due(session, now=now, window=timedelta(minutes=10))
    assert len(first) == 1 and len(second) == 0


def test_scheduler_reset_allows_reenqueue(session, defs_service,
                                          actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, cron="*/5 * * * *")
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    now = datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc)
    scheduler.enqueue_due(session, now=now, window=timedelta(minutes=10))
    scheduler.reset()
    again = scheduler.enqueue_due(session, now=now, window=timedelta(minutes=10))
    assert len(again) == 1


def test_scheduler_no_due_when_future_only(session, defs_service,
                                           actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, cron="0 0 1 1 *")  # Jan 1 midnight
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    # A tiny window well after the last Jan 1 fire => nothing due.
    now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    runs = scheduler.enqueue_due(session, now=now, window=timedelta(seconds=60))
    assert runs == []


def test_scheduler_tick_delegates_to_enqueue_due(session, defs_service,
                                                 actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, cron="* * * * *")
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    assert isinstance(scheduler.tick(session), list)


def test_scheduler_peek_next_runs(session, defs_service, actions_service,
                                  triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, cron="*/15 * * * *")
    scheduler = WorkflowScheduler(queue=InMemoryWorkflowQueue())
    peeks = scheduler.peek_next_runs(session, limit=5)
    assert len(peeks) == 1
    assert isinstance(peeks[0], ScheduledRun)
    assert peeks[0].next_run_at > datetime.now(timezone.utc)


def test_scheduler_enqueue_failure_isolated(session, defs_service,
                                            actions_service, triggers_service):
    wf = _make_workflow(defs_service, actions_service, session)
    _make_trigger(triggers_service, session, wf, cron="*/5 * * * *")

    class BrokenQueue(InMemoryWorkflowQueue):
        def enqueue(self, *a, **kw):
            raise RuntimeError("boom")

    scheduler = WorkflowScheduler(queue=BrokenQueue())
    now = datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc)
    runs = scheduler.enqueue_due(session, now=now, window=timedelta(minutes=10))
    assert len(runs) == 1
    assert runs[0].enqueued is False
    assert "boom" in (runs[0].skipped_reason or "")


def test_scheduled_run_dataclass_defaults():
    run = ScheduledRun(
        workflow_id=uuid.uuid4(),
        trigger_id=uuid.uuid4(),
        cron="* * * * *",
        next_run_at=datetime.now(timezone.utc),
    )
    assert run.enqueued is False
    assert run.enqueue_result is None
    assert run.metadata == {}


# --------------------------------------------------------------------------- #
# Task / retry
# --------------------------------------------------------------------------- #


def test_run_workflow_execution_returns_result(session, runtime_service,
                                               defs_service, actions_service):
    wf = _make_workflow(defs_service, actions_service, session, trigger_type="manual")
    payload = run_workflow_execution(
        wf.id,
        metadata={"dry_run": True},
        session_factory=lambda: session,
        runtime_service=runtime_service,
    )

    assert payload["success"] is True
    assert payload["workflowId"] == str(wf.id)
    assert "executionId" in payload
    assert payload["duration"] >= 0


def test_run_workflow_execution_closes_session(session, runtime_service,
                                               defs_service, actions_service):
    wf = _make_workflow(defs_service, actions_service, session, trigger_type="manual")
    closed = {"n": 0}

    class Wrapper:
        def __init__(self, s):
            self._s = s

        def __getattr__(self, name):
            return getattr(self._s, name)

        def close(self):
            closed["n"] += 1

    run_workflow_execution(
        wf.id,
        metadata={"dry_run": True},
        session_factory=lambda: Wrapper(session),
        runtime_service=runtime_service,
    )
    assert closed["n"] == 1


def test_run_workflow_execution_forwards_metadata(session, runtime_service,
                                                  defs_service, actions_service):
    wf = _make_workflow(defs_service, actions_service, session, trigger_type="manual")
    payload = run_workflow_execution(
        wf.id,
        metadata={"src": "task", "dry_run": True},
        session_factory=lambda: session,
        runtime_service=runtime_service,
    )
    assert payload["success"] is True


def test_compute_countdown_exponential_growth():
    values = [_compute_countdown(i, 10, jitter=False) for i in range(4)]
    assert values == [10.0, 20.0, 40.0, 80.0]


def test_compute_countdown_jitter_is_deterministic():
    a = _compute_countdown(3, 10, jitter=True)
    b = _compute_countdown(3, 10, jitter=True)
    assert a == b


def test_default_retry_config_values():
    assert DEFAULT_MAX_RETRIES == 3
    assert DEFAULT_RETRY_BACKOFF == 30


def test_execute_workflow_task_registered():
    assert execute_workflow_task.name == "workflow.execute"


def test_retryable_exceptions_include_action_error():
    assert ActionExecutionError in RETRYABLE_EXCEPTIONS


def test_non_retryable_exceptions_include_invalid_workflow():
    assert InvalidWorkflowError in NON_RETRYABLE_EXCEPTIONS
    assert UnknownActionError in NON_RETRYABLE_EXCEPTIONS


def test_task_non_retryable_bubbles(monkeypatch):
    def boom(*a, **kw):
        raise InvalidWorkflowError("bad", details={})

    monkeypatch.setattr(
        "app.runtime.scheduler.tasks.run_workflow_execution", boom
    )
    with pytest.raises(InvalidWorkflowError):
        execute_workflow_task.apply(
            kwargs={"workflow_id": str(uuid.uuid4())}, throw=True
        ).get()


def test_task_retryable_retries(monkeypatch):
    calls = {"n": 0}

    def flaky(*a, **kw):
        calls["n"] += 1
        raise ActionExecutionError("transient", details={})

    monkeypatch.setattr(
        "app.runtime.scheduler.tasks.run_workflow_execution", flaky
    )
    async_result = execute_workflow_task.apply(
        kwargs={"workflow_id": str(uuid.uuid4())}
    )
    # eager mode surfaces the final exception after retries are exhausted
    assert calls["n"] >= 1
    assert async_result.failed()


def test_task_happy_path(monkeypatch):
    def ok(*a, **kw):
        return {"executionId": "abc", "status": "completed", "success": True,
                "duration": 0.01, "workflowId": kw.get("workflow_id") or a[0]}

    monkeypatch.setattr(
        "app.runtime.scheduler.tasks.run_workflow_execution", ok
    )
    async_result = execute_workflow_task.apply(
        kwargs={"workflow_id": str(uuid.uuid4())}
    )
    assert async_result.successful()
    assert async_result.result["status"] == "completed"


# --------------------------------------------------------------------------- #
# Configuration loading / misc
# --------------------------------------------------------------------------- #


def test_queue_constants_are_unique():
    assert len(set(WORKFLOW_QUEUES)) == len(WORKFLOW_QUEUES)


def test_enqueue_result_is_frozen():
    result = EnqueueResult(task_id="a", queue="workflow", workflow_id="b")
    with pytest.raises(Exception):
        result.task_id = "changed"  # type: ignore[misc]



def test_default_workflow_queue_returns_workflow_queue_instance():
    assert isinstance(default_workflow_queue(), WorkflowQueue)


def test_set_default_workflow_queue_returns_previous():
    original = default_workflow_queue()
    swap = InMemoryWorkflowQueue()
    prev = set_default_workflow_queue(swap)
    try:
        assert prev is original
    finally:
        set_default_workflow_queue(original)
