"""Runtime executor + registry tests (Phase 8.1)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.workflow import (
    ACTION_TYPE_AUDIT,
    ACTION_TYPE_ANALYTICS,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_WEBHOOK,
    STEP_STATUS_COMPLETED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
)
from app.core.exceptions import ValidationError
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
from app.runtime import (
    ActionRegistry,
    ActionResult,
    BaseActionHandler,
    ExecutionResult,
    HandlerRegistrationError,
    InvalidWorkflowError,
    UnknownActionError,
    WorkflowExecutionContext,
    WorkflowRuntimeExecutor,
    WorkflowRuntimeService,
    default_registry,
    load_default_handlers,
)
from app.runtime.action_handlers import (
    AnalyticsHandler,
    AuditHandler,
    EntityUpdateHandler,
    NotificationHandler,
    WebhookHandler,
)
from app.runtime.exceptions import ActionExecutionError, WorkflowRuntimeError
from app.runtime.result import _now
from app.services.workflow import (
    WorkflowActionService,
    WorkflowDefinitionService,
    WorkflowExecutionService,
)


# --------------------------------------------------------------------------- #
# SQLite engine (JSONB→JSON, drop cross-module FKs)
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
# Fresh services per test (avoids sharing global singletons).
# --------------------------------------------------------------------------- #


@pytest.fixture
def defs_repo():
    return WorkflowDefinitionRepository()


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
def triggers_repo():
    return WorkflowTriggerRepository()


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
def registry():
    return ActionRegistry()


@pytest.fixture
def runtime(registry, executions_service, defs_repo, actions_repo):
    return WorkflowRuntimeExecutor(
        registry=registry,
        execution_service=executions_service,
        definitions_repo=defs_repo,
        actions_repo=actions_repo,
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_workflow(
    defs_service, actions_service, session, *, actions
) -> WorkflowDefinition:
    wf = defs_service.create_workflow(
        session,
        name=f"wf-{uuid.uuid4().hex[:8]}",
        trigger_type="manual",
    )
    for i, (atype, cfg) in enumerate(actions, start=1):
        actions_service.create_action(
            session,
            workflow_definition_id=wf.id,
            sequence=i,
            action_type=atype,
            configuration=cfg,
        )
    return wf


class _RecordingHandler(BaseActionHandler):
    action_type = "recording"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, context, config):
        self.calls.append({"config": config, "wf": context.workflow_id})
        now = _now()
        return ActionResult(
            action_type=self.action_type,
            success=True,
            status=STEP_STATUS_COMPLETED,
            started_at=now,
            completed_at=now,
            output={"ok": True},
            handler=self.name,
        )


class _FailingHandler(BaseActionHandler):
    action_type = "boom"

    def execute(self, context, config):
        raise ActionExecutionError("kaboom", retryable=True)


class _CrashingHandler(BaseActionHandler):
    action_type = "crash"

    def execute(self, context, config):
        raise RuntimeError("uncaught")


# --------------------------------------------------------------------------- #
# Result objects
# --------------------------------------------------------------------------- #


def test_action_result_duration_and_serialization():
    now = _now()
    later = _now()
    r = ActionResult(
        action_type="notification",
        success=True,
        status=STEP_STATUS_COMPLETED,
        started_at=now,
        completed_at=later,
    )
    assert r.duration >= 0.0
    payload = r.to_dict()
    assert payload["actionType"] == "notification"
    assert payload["success"] is True
    assert payload["status"] == STEP_STATUS_COMPLETED


def test_execution_result_serialization():
    now = _now()
    r = ExecutionResult(
        workflow_id="w",
        execution_id="e",
        success=False,
        status=WORKFLOW_STATUS_FAILED,
        started_at=now,
        completed_at=now,
        error="nope",
    )
    payload = r.to_dict()
    assert payload["workflowId"] == "w"
    assert payload["success"] is False
    assert payload["error"] == "nope"
    assert payload["steps"] == []


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def test_registry_register_and_get(registry):
    h = NotificationHandler()
    registry.register(ACTION_TYPE_NOTIFICATION, h)
    assert registry.has(ACTION_TYPE_NOTIFICATION)
    assert registry.get(ACTION_TYPE_NOTIFICATION) is h


def test_registry_duplicate_registration_rejected(registry):
    registry.register(ACTION_TYPE_AUDIT, AuditHandler())
    with pytest.raises(HandlerRegistrationError):
        registry.register(ACTION_TYPE_AUDIT, AuditHandler())


def test_registry_replace_flag(registry):
    registry.register(ACTION_TYPE_AUDIT, AuditHandler())
    new = AuditHandler()
    registry.register(ACTION_TYPE_AUDIT, new, replace=True)
    assert registry.get(ACTION_TYPE_AUDIT) is new


def test_registry_unregister(registry):
    registry.register(ACTION_TYPE_AUDIT, AuditHandler())
    registry.unregister(ACTION_TYPE_AUDIT)
    assert not registry.has(ACTION_TYPE_AUDIT)


def test_registry_unknown_action_raises(registry):
    with pytest.raises(UnknownActionError):
        registry.get("nope")


def test_registry_rejects_non_handler(registry):
    with pytest.raises(HandlerRegistrationError):
        registry.register("x", object())  # type: ignore[arg-type]


def test_registry_rejects_empty_name(registry):
    with pytest.raises(HandlerRegistrationError):
        registry.register("", NotificationHandler())


def test_registry_registered_types_sorted(registry):
    registry.register("b", NotificationHandler())
    registry.register("a", AuditHandler())
    assert registry.registered_types() == ["a", "b"]


def test_registry_clear(registry):
    registry.register("a", AuditHandler())
    registry.clear()
    assert registry.registered_types() == []


def test_registry_execute_dispatches(registry):
    h = _RecordingHandler()
    registry.register(h.action_type, h)
    wf = WorkflowDefinition(id=uuid.uuid4(), name="x", trigger_type="manual")
    ctx = WorkflowExecutionContext(workflow=wf, execution=None)
    res = registry.execute(h.action_type, ctx, {"any": 1})
    assert res.success and h.calls[0]["config"] == {"any": 1}


# --------------------------------------------------------------------------- #
# Placeholder handlers
# --------------------------------------------------------------------------- #


def test_notification_handler_validates_required_keys():
    h = NotificationHandler()
    with pytest.raises(ValidationError):
        h.validate({})


def test_notification_handler_success():
    h = NotificationHandler()
    wf = WorkflowDefinition(id=uuid.uuid4(), name="x", trigger_type="manual")
    ctx = WorkflowExecutionContext(workflow=wf, execution=None)
    res = h.execute(ctx, {"title": "hi", "message": "there", "user_id": "u"})
    assert res.success and res.status == STEP_STATUS_COMPLETED


def test_webhook_handler_rejects_bad_url():
    h = WebhookHandler()
    with pytest.raises(ValidationError):
        h.validate({"url": "ftp://x"})


def test_webhook_handler_accepts_https():
    h = WebhookHandler()
    h.validate({"url": "https://example.com"})


def test_all_default_handlers_have_action_type():
    for cls in (
        NotificationHandler,
        AuditHandler,
        AnalyticsHandler,
        WebhookHandler,
        EntityUpdateHandler,
    ):
        assert cls().action_type


def test_base_handler_supports_retry_default():
    assert NotificationHandler().supports_retry() is True


# --------------------------------------------------------------------------- #
# Context
# --------------------------------------------------------------------------- #


def test_context_exposes_workflow_and_execution_ids():
    wf = WorkflowDefinition(id=uuid.uuid4(), name="x", trigger_type="manual")
    ctx = WorkflowExecutionContext(workflow=wf, execution=None)
    assert ctx.workflow_id == str(wf.id)
    assert ctx.execution_id is None


def test_context_is_frozen():
    wf = WorkflowDefinition(id=uuid.uuid4(), name="x", trigger_type="manual")
    ctx = WorkflowExecutionContext(workflow=wf, execution=None)
    with pytest.raises(Exception):
        ctx.variables = {"x": 1}  # type: ignore[misc]


def test_context_bind_logger_returns_bound():
    wf = WorkflowDefinition(id=uuid.uuid4(), name="x", trigger_type="manual")
    ctx = WorkflowExecutionContext(workflow=wf, execution=None)
    logger = ctx.bind_logger(foo="bar")
    assert logger is not None


# --------------------------------------------------------------------------- #
# Executor
# --------------------------------------------------------------------------- #


def test_executor_validate_rejects_disabled_workflow(runtime):
    wf = WorkflowDefinition(
        id=uuid.uuid4(), name="x", trigger_type="manual", enabled=False
    )
    with pytest.raises(InvalidWorkflowError):
        runtime.validate_workflow(wf, [])


def test_executor_validate_rejects_no_actions(runtime):
    wf = WorkflowDefinition(
        id=uuid.uuid4(), name="x", trigger_type="manual", enabled=True
    )
    with pytest.raises(InvalidWorkflowError):
        runtime.validate_workflow(wf, [])


def test_executor_validate_rejects_unknown_handler(runtime):
    wf = WorkflowDefinition(
        id=uuid.uuid4(), name="x", trigger_type="manual", enabled=True
    )
    action = WorkflowAction(
        id=uuid.uuid4(),
        workflow_definition_id=wf.id,
        sequence=1,
        action_type="mystery",
        enabled=True,
    )
    with pytest.raises(UnknownActionError):
        runtime.validate_workflow(wf, [action])


def test_executor_missing_workflow_raises(session, runtime):
    with pytest.raises(InvalidWorkflowError):
        runtime.execute(session, uuid.uuid4())


def test_executor_runs_all_actions(
    session, runtime, registry, defs_service, actions_service
):
    registry.register(ACTION_TYPE_NOTIFICATION, NotificationHandler())
    registry.register(ACTION_TYPE_AUDIT, AuditHandler())
    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[
            (ACTION_TYPE_NOTIFICATION, {"title": "t", "message": "m", "user_id": "u"}),
            (ACTION_TYPE_AUDIT, {"event": "x"}),
        ],
    )
    result = runtime.execute(session, wf.id, trigger_event="manual", metadata={"dry_run": True})
    assert result.success is True
    assert result.status == WORKFLOW_STATUS_COMPLETED
    assert len(result.steps) == 2
    assert all(s.success for s in result.steps)


def test_executor_stops_on_action_failure(
    session, runtime, registry, defs_service, actions_service
):
    class _FailingWebhook(BaseActionHandler):
        action_type = ACTION_TYPE_WEBHOOK

        def execute(self, context, config):
            raise ActionExecutionError("no", retryable=False)

    registry.register(ACTION_TYPE_NOTIFICATION, NotificationHandler())
    registry.register(ACTION_TYPE_WEBHOOK, _FailingWebhook())
    registry.register(ACTION_TYPE_AUDIT, AuditHandler())

    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[
            (ACTION_TYPE_NOTIFICATION, {"title": "t", "message": "m", "user_id": "u"}),
            (ACTION_TYPE_WEBHOOK, {"url": "https://x"}),
            (ACTION_TYPE_AUDIT, {"event": "later"}),
        ],
    )
    result = runtime.execute(session, wf.id, stop_on_failure=True, metadata={"dry_run": True})
    assert result.success is False
    assert result.status == WORKFLOW_STATUS_FAILED
    assert len(result.steps) == 2  # third action skipped
    assert result.steps[-1].error == "no"


def test_executor_continues_on_failure_when_flag_off(
    session, runtime, registry, defs_service, actions_service
):
    class _FailingAnalytics(BaseActionHandler):
        action_type = ACTION_TYPE_ANALYTICS

        def execute(self, context, config):
            raise ActionExecutionError("nope")

    registry.register(ACTION_TYPE_ANALYTICS, _FailingAnalytics())
    registry.register(ACTION_TYPE_NOTIFICATION, NotificationHandler())
    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[
            (ACTION_TYPE_ANALYTICS, {"metric": "m"}),
            (ACTION_TYPE_NOTIFICATION, {"title": "t", "message": "m", "user_id": "u"}),
        ],
    )
    result = runtime.execute(session, wf.id, stop_on_failure=False, metadata={"dry_run": True})
    assert result.status == WORKFLOW_STATUS_FAILED
    assert len(result.steps) == 2
    assert result.steps[0].success is False
    assert result.steps[1].success is True


def test_executor_isolates_handler_crashes(
    session, runtime, registry, defs_service, actions_service
):
    class _Crashing(BaseActionHandler):
        action_type = ACTION_TYPE_WEBHOOK

        def execute(self, context, config):
            raise RuntimeError("uncaught")

    registry.register(ACTION_TYPE_WEBHOOK, _Crashing())
    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[(ACTION_TYPE_WEBHOOK, {"url": "https://x"})],
    )
    result = runtime.execute(session, wf.id, metadata={"dry_run": True})
    assert result.success is False
    assert result.steps[0].error == "uncaught"
    assert result.steps[0].retryable is True


def test_executor_skips_disabled_actions(
    session, runtime, registry, defs_service, actions_service, actions_repo
):
    registry.register(ACTION_TYPE_NOTIFICATION, NotificationHandler())
    registry.register(ACTION_TYPE_AUDIT, AuditHandler())
    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[
            (ACTION_TYPE_NOTIFICATION, {"title": "t", "message": "m", "user_id": "u"}),
            (ACTION_TYPE_AUDIT, {"event": "x"}),
        ],
    )
    # Disable the second action.
    actions = actions_repo.ordered_actions(session, wf.id)
    actions_service.update_action(session, actions[1].id, enabled=False)
    result = runtime.execute(session, wf.id, metadata={"dry_run": True})
    assert result.success is True
    assert len(result.steps) == 1
    assert result.steps[0].action_type == ACTION_TYPE_NOTIFICATION


def test_executor_persists_execution_and_steps(
    session,
    runtime,
    registry,
    defs_service,
    actions_service,
    executions_repo,
    steps_repo,
):
    registry.register(ACTION_TYPE_NOTIFICATION, NotificationHandler())
    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[(ACTION_TYPE_NOTIFICATION, {"title": "t", "message": "m", "user_id": "u"})],
    )
    result = runtime.execute(session, wf.id, trigger_event="unit-test", metadata={"dry_run": True})
    assert result.execution_id is not None
    exec_obj = executions_repo.get_execution(session, uuid.UUID(result.execution_id))
    assert exec_obj is not None
    assert exec_obj.status == WORKFLOW_STATUS_COMPLETED
    steps, total = steps_repo.list_steps(
        session, workflow_execution_id=exec_obj.id
    )
    assert total == 1 and steps[0].status == STEP_STATUS_COMPLETED


def test_executor_records_failed_step_and_marks_execution_failed(
    session, runtime, registry, defs_service, actions_service, executions_repo
):
    class _F(BaseActionHandler):
        action_type = ACTION_TYPE_WEBHOOK

        def execute(self, context, config):
            raise ActionExecutionError("bad")

    registry.register(ACTION_TYPE_WEBHOOK, _F())
    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[(ACTION_TYPE_WEBHOOK, {"url": "https://x"})],
    )
    result = runtime.execute(session, wf.id, metadata={"dry_run": True})
    assert result.status == WORKFLOW_STATUS_FAILED
    exec_obj = executions_repo.get_execution(session, uuid.UUID(result.execution_id))
    assert exec_obj.status == WORKFLOW_STATUS_FAILED
    assert exec_obj.failure_reason == "bad"


def test_executor_ephemeral_mode_does_not_persist(
    session,
    runtime,
    registry,
    defs_service,
    actions_service,
    executions_repo,
):
    registry.register(ACTION_TYPE_NOTIFICATION, NotificationHandler())
    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[(ACTION_TYPE_NOTIFICATION, {"title": "t", "message": "m", "user_id": "u"})],
    )
    result = runtime.execute(session, wf.id, persist=False, metadata={"dry_run": True})
    assert result.success is True
    assert result.execution_id is None
    _, total = executions_repo.list_executions(session, workflow_definition_id=wf.id)
    assert total == 0


# --------------------------------------------------------------------------- #
# Service facade
# --------------------------------------------------------------------------- #


def test_service_load_handlers_registers_defaults():
    reg = ActionRegistry()
    svc = WorkflowRuntimeService(registry=reg)
    loaded = svc.load_handlers()
    assert ACTION_TYPE_NOTIFICATION in loaded
    assert reg.has(ACTION_TYPE_WEBHOOK)
    assert reg.has(ACTION_TYPE_AUDIT)


def test_service_validate_runtime_reports_registered_types():
    reg = ActionRegistry()
    svc = WorkflowRuntimeService(registry=reg)
    svc.load_handlers()
    diag = svc.validate_runtime()
    assert ACTION_TYPE_NOTIFICATION in diag["registeredActions"]
    assert "NotificationHandler" in diag["defaultHandlers"]
    assert diag["checkedAt"]


def test_service_execute_step_runs_single_action(
    session, defs_service, actions_service
):
    reg = ActionRegistry()
    svc = WorkflowRuntimeService(registry=reg)
    svc.load_handlers()
    wf = _make_workflow(
        defs_service,
        actions_service,
        session,
        actions=[(ACTION_TYPE_NOTIFICATION, {"title": "t", "message": "m", "user_id": "u"})],
    )
    from app.repositories.workflow import workflow_actions as _ar
    action = _ar.ordered_actions(session, wf.id)[0]
    result = svc.execute_step(
        session, workflow_id=wf.id, action_id=action.id,
        metadata={"dry_run": True},
    )
    assert result.success is True
    assert result.action_type == ACTION_TYPE_NOTIFICATION


def test_service_execute_step_rejects_foreign_action(
    session, defs_service, actions_service
):
    reg = ActionRegistry()
    svc = WorkflowRuntimeService(registry=reg)
    svc.load_handlers()
    wf1 = _make_workflow(
        defs_service, actions_service, session,
        actions=[(ACTION_TYPE_NOTIFICATION, {"title": "t", "message": "m", "user_id": "u"})],
    )
    wf2 = _make_workflow(
        defs_service, actions_service, session,
        actions=[(ACTION_TYPE_AUDIT, {"event": "x"})],
    )
    from app.repositories.workflow import workflow_actions as _ar
    foreign = _ar.ordered_actions(session, wf2.id)[0]
    with pytest.raises(InvalidWorkflowError):
        svc.execute_step(session, workflow_id=wf1.id, action_id=foreign.id)


def test_load_default_handlers_module_helper_populates_default_registry():
    default_registry.clear()
    loaded = load_default_handlers()
    assert ACTION_TYPE_NOTIFICATION in loaded
    assert default_registry.has(ACTION_TYPE_WEBHOOK)


# --------------------------------------------------------------------------- #
# Exception hierarchy
# --------------------------------------------------------------------------- #


def test_exception_hierarchy():
    for exc in (
        InvalidWorkflowError("x"),
        UnknownActionError("x"),
        HandlerRegistrationError("x"),
        ActionExecutionError("x"),
    ):
        assert isinstance(exc, WorkflowRuntimeError)


def test_action_execution_error_carries_metadata():
    err = ActionExecutionError("nope", action_type="webhook", retryable=True)
    assert err.retryable is True
    assert err.action_type == "webhook"
    assert err.message == "nope"
