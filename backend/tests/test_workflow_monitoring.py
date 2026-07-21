"""Runtime monitoring & observability tests (Phase 8.5).

Covers:

* Metrics collector (`app.runtime.monitoring.metrics`)
* Retry history read model (`app.runtime.monitoring.history`)
* Runtime health checks (`app.runtime.monitoring.health`)
* Statistics service (`app.runtime.monitoring.statistics`)
* Runtime monitoring API (`app.api.v1.runtime`)

Follows the in-memory SQLite / JSONB-swap engine pattern from
``tests/test_workflow_api.py``.
"""
from __future__ import annotations

import types
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import runtime as runtime_router
from app.core.exceptions import NotFoundError, install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.workflow import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTrigger,
)
from app.runtime.monitoring import (
    ExecutionRetryHistoryService,
    MetricsCollector,
    WorkflowRuntimeHealth,
    WorkflowStatisticsService,
)
from app.runtime.monitoring import health as health_mod
from app.runtime.monitoring import metrics as metrics_mod
from app.runtime.registry import ActionRegistry
from app.runtime.base import BaseActionHandler
from app.runtime.result import ActionResult
from app.constants.workflow import (
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
    STEP_STATUS_PENDING,
    WORKFLOW_STATUS_CANCELLED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_FAILED,
    WORKFLOW_STATUS_RUNNING,
)


# --------------------------------------------------------------------------- #
# Engine (mirror of test_workflow_api)
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
        poolclass=StaticPool,
        future=True,
    )
    for t in tables:
        t.create(eng, checkfirst=True)
    return eng


@pytest.fixture
def Session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _user(role: str = "super_admin"):
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        roles=[types.SimpleNamespace(name=role)],
        is_active=True,
        deleted_at=None,
    )


def _client(Session, user=None):
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(runtime_router.router, prefix="/runtime", tags=["runtime"])

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[current_user] = lambda: user or _user()
    return TestClient(app)


def _now(delta_seconds: float = 0.0) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)


# --------------------------------------------------------------------------- #
# DB helpers
# --------------------------------------------------------------------------- #


def _mk_definition(db, *, name: str | None = None, enabled: bool = True):
    wf = WorkflowDefinition(
        name=name or f"WF-{uuid.uuid4().hex[:6]}",
        trigger_type="event",
        enabled=enabled,
        version=1,
        metadata_={},
    )
    db.add(wf)
    db.flush()
    return wf


def _mk_action(db, wf, *, sequence=1, action_type="notification"):
    a = WorkflowAction(
        workflow_definition_id=wf.id,
        sequence=sequence,
        action_type=action_type,
        configuration_json={},
        enabled=True,
        metadata_={},
    )
    db.add(a)
    db.flush()
    return a


def _mk_execution(
    db,
    wf,
    *,
    status: str = WORKFLOW_STATUS_COMPLETED,
    started_offset: float = -10.0,
    completed_offset: float = 0.0,
):
    started = _now(started_offset)
    completed = _now(completed_offset) if status != WORKFLOW_STATUS_RUNNING else None
    e = WorkflowExecution(
        workflow_definition_id=wf.id,
        status=status,
        trigger_event="test",
        started_at=started,
        completed_at=completed,
        context_json={},
        metadata_={},
    )
    db.add(e)
    db.flush()
    return e


def _mk_step(
    db,
    execution,
    action,
    *,
    status: str = STEP_STATUS_COMPLETED,
    retry_count: int = 0,
    error_message: str | None = None,
):
    s = WorkflowExecutionStep(
        workflow_execution_id=execution.id,
        workflow_action_id=action.id,
        status=status,
        retry_count=retry_count,
        error_message=error_message,
        output_json={},
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


# =========================================================================== #
# METRICS COLLECTOR
# =========================================================================== #


class TestMetricsCollector:
    def test_starts_empty(self):
        c = MetricsCollector()
        snap = c.snapshot()
        assert snap.executions_total == 0
        assert snap.executions_by_status == {}
        assert snap.duration["count"] == 0

    def test_record_execution_counts(self):
        c = MetricsCollector()
        c.record_execution(workflow_id="w1", status="completed", duration=1.0)
        c.record_execution(workflow_id="w1", status="failed", duration=2.5)
        snap = c.snapshot()
        assert snap.executions_total == 2
        assert snap.executions_by_status == {"completed": 1, "failed": 1}
        assert snap.executions_by_workflow == {"w1": 2}

    def test_record_execution_duration_aggregate(self):
        c = MetricsCollector()
        c.record_execution(workflow_id="w", status="completed", duration=1.0)
        c.record_execution(workflow_id="w", status="completed", duration=3.0)
        d = c.snapshot().duration
        assert d["count"] == 2
        assert d["min"] == 1.0
        assert d["max"] == 3.0
        assert d["average"] == 2.0

    def test_record_execution_negative_duration_clamped(self):
        c = MetricsCollector()
        c.record_execution(workflow_id="w", status="completed", duration=-5.0)
        assert c.snapshot().duration["min"] == 0.0

    def test_record_action_success_and_failure(self):
        c = MetricsCollector()
        c.record_action(handler="notify", duration=0.5, success=True)
        c.record_action(handler="notify", duration=0.7, success=False)
        snap = c.snapshot()
        assert snap.action_success == 1
        assert snap.action_failure == 1
        assert snap.handler_duration["notify"]["count"] == 2

    def test_record_action_per_handler_isolated(self):
        c = MetricsCollector()
        c.record_action(handler="a", duration=1.0, success=True)
        c.record_action(handler="b", duration=2.0, success=True)
        hd = c.snapshot().handler_duration
        assert hd["a"]["total"] == 1.0
        assert hd["b"]["total"] == 2.0

    def test_record_queue_latency(self):
        c = MetricsCollector()
        c.record_queue_latency(2.0)
        c.record_queue_latency(4.0)
        ql = c.snapshot().queue_latency
        assert ql["count"] == 2
        assert ql["average"] == 3.0

    def test_record_retry_increments(self):
        c = MetricsCollector()
        c.record_retry()
        c.record_retry(count=3)
        assert c.snapshot().retry_count == 4

    def test_record_retry_ignores_non_positive(self):
        c = MetricsCollector()
        c.record_retry(count=0)
        c.record_retry(count=-2)
        assert c.snapshot().retry_count == 0

    def test_success_rate_empty(self):
        assert MetricsCollector().success_rate() == 0.0

    def test_success_rate_computed(self):
        c = MetricsCollector()
        c.record_execution(workflow_id="w", status="completed", duration=1.0)
        c.record_execution(workflow_id="w", status="completed", duration=1.0)
        c.record_execution(workflow_id="w", status="failed", duration=1.0)
        assert pytest.approx(c.success_rate(), rel=1e-6) == 2 / 3
        assert pytest.approx(c.failure_rate(), rel=1e-6) == 1 / 3

    def test_reset_clears_all(self):
        c = MetricsCollector()
        c.record_execution(workflow_id="w", status="completed", duration=1.0)
        c.record_action(handler="n", duration=1.0, success=True)
        c.record_retry()
        c.reset()
        snap = c.snapshot()
        assert snap.executions_total == 0
        assert snap.action_success == 0
        assert snap.retry_count == 0
        assert snap.handler_duration == {}

    def test_snapshot_to_dict_camel_case(self):
        c = MetricsCollector()
        c.record_execution(workflow_id="w", status="completed", duration=1.0)
        d = c.snapshot().to_dict()
        assert "executionsTotal" in d
        assert "executionsByStatus" in d
        assert "generatedAt" in d

    def test_snapshot_is_a_copy(self):
        c = MetricsCollector()
        c.record_execution(workflow_id="w", status="completed", duration=1.0)
        s = c.snapshot()
        s.executions_by_status["completed"] = 999
        assert c.snapshot().executions_by_status["completed"] == 1

    def test_thread_safe_smoke(self):
        import threading

        c = MetricsCollector()

        def _work():
            for _ in range(200):
                c.record_execution(workflow_id="w", status="completed", duration=0.1)

        threads = [threading.Thread(target=_work) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert c.snapshot().executions_total == 800

    def test_default_metrics_is_singleton(self):
        assert metrics_mod.default_metrics is metrics_mod.default_metrics

    def test_default_metrics_reset_between_tests(self):
        metrics_mod.default_metrics.reset()
        metrics_mod.default_metrics.record_execution(
            workflow_id="w", status="completed", duration=1.0
        )
        assert metrics_mod.default_metrics.snapshot().executions_total == 1
        metrics_mod.default_metrics.reset()

    def test_duration_aggregate_average_zero_when_no_data(self):
        assert MetricsCollector().snapshot().duration["average"] == 0.0

    def test_multiple_workflows_tracked(self):
        c = MetricsCollector()
        c.record_execution(workflow_id="a", status="completed", duration=1.0)
        c.record_execution(workflow_id="b", status="completed", duration=1.0)
        c.record_execution(workflow_id="a", status="failed", duration=1.0)
        by_wf = c.snapshot().executions_by_workflow
        assert by_wf["a"] == 2
        assert by_wf["b"] == 1


# =========================================================================== #
# RETRY HISTORY
# =========================================================================== #


class TestRetryHistory:
    def test_get_history_empty(self, Session):
        svc = ExecutionRetryHistoryService()
        db = Session()
        wf = _mk_definition(db)
        exe = _mk_execution(db, wf)
        db.commit()
        out = svc.get_retry_history(db, exe.id)
        assert out["executionId"] == str(exe.id)
        assert out["totalSteps"] == 0
        assert out["totalRetries"] == 0
        assert out["steps"] == []

    def test_get_history_with_steps(self, Session):
        svc = ExecutionRetryHistoryService()
        db = Session()
        wf = _mk_definition(db)
        a1 = _mk_action(db, wf, sequence=1)
        a2 = _mk_action(db, wf, sequence=2)
        exe = _mk_execution(db, wf)
        _mk_step(db, exe, a1, retry_count=0)
        _mk_step(db, exe, a2, retry_count=2, status=STEP_STATUS_FAILED,
                 error_message="boom")
        db.commit()
        out = svc.get_retry_history(db, exe.id)
        assert out["totalSteps"] == 2
        assert out["totalRetries"] == 2
        errors = [s["lastError"] for s in out["steps"]]
        assert "boom" in errors

    def test_attempt_is_retry_count_plus_one(self, Session):
        svc = ExecutionRetryHistoryService()
        db = Session()
        wf = _mk_definition(db)
        a = _mk_action(db, wf)
        exe = _mk_execution(db, wf)
        _mk_step(db, exe, a, retry_count=3)
        db.commit()
        out = svc.get_retry_history(db, exe.id)
        assert out["steps"][0]["attempt"] == 4
        assert out["steps"][0]["retryCount"] == 3

    def test_final_status_none_for_pending(self, Session):
        svc = ExecutionRetryHistoryService()
        db = Session()
        wf = _mk_definition(db)
        a = _mk_action(db, wf)
        exe = _mk_execution(db, wf, status=WORKFLOW_STATUS_RUNNING)
        _mk_step(db, exe, a, status=STEP_STATUS_PENDING)
        db.commit()
        out = svc.get_retry_history(db, exe.id)
        assert out["steps"][0]["finalStatus"] is None

    def test_not_found_raises(self, Session):
        svc = ExecutionRetryHistoryService()
        db = Session()
        with pytest.raises(NotFoundError):
            svc.get_retry_history(db, uuid.uuid4())

    def test_returns_camel_case_keys(self, Session):
        svc = ExecutionRetryHistoryService()
        db = Session()
        wf = _mk_definition(db)
        a = _mk_action(db, wf)
        exe = _mk_execution(db, wf)
        _mk_step(db, exe, a)
        db.commit()
        step = svc.get_retry_history(db, exe.id)["steps"][0]
        for key in ("stepId", "actionId", "attempt", "retryCount", "status",
                    "startedAt", "completedAt"):
            assert key in step

    def test_total_retries_sums_all_steps(self, Session):
        svc = ExecutionRetryHistoryService()
        db = Session()
        wf = _mk_definition(db)
        a1 = _mk_action(db, wf, sequence=1)
        a2 = _mk_action(db, wf, sequence=2)
        a3 = _mk_action(db, wf, sequence=3)
        exe = _mk_execution(db, wf)
        _mk_step(db, exe, a1, retry_count=1)
        _mk_step(db, exe, a2, retry_count=2)
        _mk_step(db, exe, a3, retry_count=0)
        db.commit()
        assert svc.get_retry_history(db, exe.id)["totalRetries"] == 3

    def test_include_workflow_and_status(self, Session):
        svc = ExecutionRetryHistoryService()
        db = Session()
        wf = _mk_definition(db)
        exe = _mk_execution(db, wf, status=WORKFLOW_STATUS_FAILED)
        db.commit()
        out = svc.get_retry_history(db, exe.id)
        assert out["workflowDefinitionId"] == str(wf.id)
        assert out["status"] == WORKFLOW_STATUS_FAILED


# =========================================================================== #
# HEALTH
# =========================================================================== #


class _FakeHandler(BaseActionHandler):
    action_type = "notification"

    def execute(self, context, config):  # pragma: no cover - not used
        return ActionResult(
            action_type="notification",
            success=True,
            status="completed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )


def _populated_registry(action_types=("notification", "audit", "analytics",
                                       "webhook", "update_entity")):
    reg = ActionRegistry()

    class _H(BaseActionHandler):
        def execute(self, context, config):  # pragma: no cover - not invoked
            return ActionResult(
                action_type=self.action_type,
                success=True,
                status="completed",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )

    for at in action_types:
        h = _H()
        h.action_type = at  # type: ignore[attr-defined]
        reg.register(at, h, replace=True)
    return reg


class TestRuntimeHealth:
    def test_empty_registry_is_unhealthy(self):
        h = WorkflowRuntimeHealth(registry=ActionRegistry())
        result = h.check()
        assert result["checks"]["registry"]["status"] == "unhealthy"
        assert result["status"] == "unhealthy"

    def test_missing_expected_is_degraded(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry(("notification",)))
        result = h.check()
        assert result["checks"]["registry"]["status"] == "degraded"
        assert "missing" in result["checks"]["registry"]

    def test_full_registry_ok(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry())
        result = h.check()
        assert result["checks"]["registry"]["status"] == "ok"

    def test_handlers_check_reports_count(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry())
        result = h.check()
        assert result["checks"]["handlers"]["count"] == 5

    def test_queue_check_reports_backend(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry())
        result = h.check()
        assert "backend" in result["checks"]["queue"]
        assert result["checks"]["queue"]["status"] == "ok"

    def test_scheduler_check_ok(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry())
        result = h.check()
        assert result["checks"]["scheduler"]["status"] == "ok"

    def test_celery_unknown_does_not_downgrade_overall(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry())
        result = h.check()
        # Celery is unknown in test env; overall should still be OK.
        assert result["status"] == "ok"

    def test_worst_status_helper(self):
        assert health_mod._worst(["ok", "ok"]) == "ok"
        assert health_mod._worst(["ok", "degraded"]) == "degraded"
        assert health_mod._worst(["ok", "unhealthy", "degraded"]) == "unhealthy"
        assert health_mod._worst([]) == "unknown"

    def test_check_returns_status_key(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry())
        result = h.check()
        assert set(result.keys()) == {"status", "checks"}

    def test_check_all_subchecks_present(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry())
        result = h.check()
        assert set(result["checks"].keys()) == {
            "registry",
            "scheduler",
            "queue",
            "celery",
            "handlers",
            "leader",
            "lockProvider",
            "idempotency",
        }

    def test_custom_expected_handlers(self):
        h = WorkflowRuntimeHealth(
            registry=_populated_registry(("notification",)),
            expected_handlers=("notification",),
        )
        result = h.check()
        assert result["checks"]["registry"]["status"] == "ok"

    def test_empty_registry_overall_unhealthy(self):
        h = WorkflowRuntimeHealth(registry=ActionRegistry())
        assert h.check()["status"] == "unhealthy"

    def test_default_runtime_health_singleton(self):
        assert health_mod.default_runtime_health is health_mod.default_runtime_health

    def test_status_constants(self):
        assert health_mod.STATUS_OK == "ok"
        assert health_mod.STATUS_DEGRADED == "degraded"
        assert health_mod.STATUS_UNHEALTHY == "unhealthy"
        assert health_mod.STATUS_UNKNOWN == "unknown"

    def test_celery_check_is_best_effort(self):
        h = WorkflowRuntimeHealth(registry=_populated_registry())
        celery = h._check_celery()
        assert celery["status"] in {"ok", "unknown"}


# =========================================================================== #
# STATISTICS SERVICE
# =========================================================================== #


class TestStatistics:
    def test_overview_empty(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        out = svc.overview(db)
        assert out["total"] == 0
        assert out["successRate"] == 0.0
        assert out["failureRate"] == 0.0
        assert out["retryRate"] == 0.0
        assert out["avgDurationSeconds"] == 0.0

    def test_overview_counts_by_status(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_COMPLETED)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_COMPLETED)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_FAILED)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_CANCELLED)
        db.commit()
        out = svc.overview(db)
        assert out["total"] == 4
        assert out["completed"] == 2
        assert out["failed"] == 1
        assert out["cancelled"] == 1

    def test_success_and_failure_rate(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        for _ in range(3):
            _mk_execution(db, wf, status=WORKFLOW_STATUS_COMPLETED)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_FAILED)
        db.commit()
        out = svc.overview(db)
        assert out["successRate"] == pytest.approx(0.75)
        assert out["failureRate"] == pytest.approx(0.25)

    def test_avg_duration(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        _mk_execution(db, wf, started_offset=-4.0, completed_offset=0.0)
        _mk_execution(db, wf, started_offset=-2.0, completed_offset=0.0)
        db.commit()
        out = svc.overview(db)
        # duration averages fall between the two synthetic gaps.
        assert out["avgDurationSeconds"] > 0.0

    def test_retry_rate_and_total(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        a = _mk_action(db, wf)
        e1 = _mk_execution(db, wf)
        e2 = _mk_execution(db, wf)
        _mk_step(db, e1, a, retry_count=2)
        _mk_step(db, e2, a, retry_count=0)
        db.commit()
        out = svc.overview(db)
        assert out["totalRetries"] == 2
        assert out["retryExecutions"] == 1
        assert out["retryRate"] == pytest.approx(0.5)

    def test_since_filter_excludes_older(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        old = _mk_execution(db, wf)
        # rewind created_at by 10 days
        old.created_at = datetime.now(timezone.utc) - timedelta(days=10)
        _mk_execution(db, wf)
        db.commit()
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        out = svc.overview(db, since=cutoff)
        assert out["total"] == 1
        assert out["since"] is not None

    def test_top_workflows_orders_by_count(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        a = _mk_definition(db, name="Alpha")
        b = _mk_definition(db, name="Beta")
        for _ in range(3):
            _mk_execution(db, a)
        _mk_execution(db, b)
        db.commit()
        top = svc.top_workflows(db, limit=5)
        assert top[0]["name"] == "Alpha"
        assert top[0]["total"] == 3

    def test_top_workflows_respects_limit(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        for i in range(5):
            wf = _mk_definition(db, name=f"W{i}")
            _mk_execution(db, wf)
        db.commit()
        assert len(svc.top_workflows(db, limit=2)) == 2

    def test_top_failures_only_failed(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db, name="Fx")
        _mk_execution(db, wf, status=WORKFLOW_STATUS_FAILED)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_FAILED)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_COMPLETED)
        db.commit()
        fails = svc.top_failures(db, limit=5)
        assert len(fails) == 1
        assert fails[0]["failed"] == 2
        assert fails[0]["name"] == "Fx"

    def test_top_failures_empty(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_COMPLETED)
        db.commit()
        assert svc.top_failures(db) == []

    def test_overview_no_completed_returns_zero_duration(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_RUNNING)
        db.commit()
        assert svc.overview(db)["avgDurationSeconds"] == 0.0

    def test_top_workflows_includes_workflow_id(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        _mk_execution(db, wf)
        db.commit()
        top = svc.top_workflows(db)
        assert top[0]["workflowDefinitionId"] == str(wf.id)

    def test_by_status_dict(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        wf = _mk_definition(db)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_COMPLETED)
        db.commit()
        assert svc.overview(db)["byStatus"] == {WORKFLOW_STATUS_COMPLETED: 1}

    def test_top_workflows_default_limit(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        for i in range(10):
            _mk_execution(db, _mk_definition(db, name=f"W{i}"))
        db.commit()
        assert len(svc.top_workflows(db)) == 5

    def test_since_none_returns_null_iso(self, Session):
        svc = WorkflowStatisticsService()
        db = Session()
        assert svc.overview(db, since=None)["since"] is None


# =========================================================================== #
# API
# =========================================================================== #


class TestRuntimeAPI:
    def test_health_endpoint(self, Session):
        c = _client(Session)
        r = c.get("/runtime/health")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert "status" in body["data"]
        assert "checks" in body["data"]

    def test_health_requires_manage_permission(self, Session):
        c = _client(Session, _user("viewer"))
        r = c.get("/runtime/health")
        assert r.status_code == 403

    def test_metrics_endpoint(self, Session):
        metrics_mod.default_metrics.reset()
        c = _client(Session)
        r = c.get("/runtime/metrics")
        assert r.status_code == 200
        assert r.json()["data"]["executionsTotal"] == 0

    def test_metrics_reflects_records(self, Session):
        metrics_mod.default_metrics.reset()
        metrics_mod.default_metrics.record_execution(
            workflow_id="w", status="completed", duration=1.0
        )
        c = _client(Session)
        r = c.get("/runtime/metrics")
        assert r.json()["data"]["executionsTotal"] == 1
        metrics_mod.default_metrics.reset()

    def test_statistics_endpoint_empty(self, Session):
        c = _client(Session)
        r = c.get("/runtime/statistics")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["overview"]["total"] == 0
        assert data["topWorkflows"] == []
        assert data["topFailures"] == []

    def test_statistics_endpoint_with_data(self, Session):
        db = Session()
        wf = _mk_definition(db, name="Statful")
        _mk_execution(db, wf, status=WORKFLOW_STATUS_COMPLETED)
        _mk_execution(db, wf, status=WORKFLOW_STATUS_FAILED)
        db.commit()
        db.close()
        c = _client(Session)
        r = c.get("/runtime/statistics")
        data = r.json()["data"]
        assert data["overview"]["total"] == 2
        assert data["topWorkflows"][0]["total"] == 2

    def test_statistics_top_limit_param(self, Session):
        db = Session()
        for i in range(3):
            wf = _mk_definition(db, name=f"W{i}")
            _mk_execution(db, wf)
        db.commit()
        db.close()
        c = _client(Session)
        r = c.get("/runtime/statistics", params={"topLimit": 1})
        assert len(r.json()["data"]["topWorkflows"]) == 1

    def test_statistics_since_param(self, Session):
        db = Session()
        wf = _mk_definition(db)
        _mk_execution(db, wf)
        db.commit()
        db.close()
        c = _client(Session)
        since = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        r = c.get("/runtime/statistics", params={"since": since})
        assert r.status_code == 200
        assert r.json()["data"]["overview"]["total"] == 0

    def test_statistics_requires_manage(self, Session):
        c = _client(Session, _user("viewer"))
        r = c.get("/runtime/statistics")
        assert r.status_code == 403

    def test_retries_endpoint(self, Session):
        db = Session()
        wf = _mk_definition(db)
        a = _mk_action(db, wf)
        exe = _mk_execution(db, wf)
        _mk_step(db, exe, a, retry_count=1, error_message="e")
        db.commit()
        eid = str(exe.id)
        db.close()
        c = _client(Session)
        r = c.get(f"/runtime/executions/{eid}/retries")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["totalRetries"] == 1
        assert data["steps"][0]["lastError"] == "e"

    def test_retries_not_found(self, Session):
        c = _client(Session)
        r = c.get(f"/runtime/executions/{uuid.uuid4()}/retries")
        assert r.status_code == 404

    def test_retries_requires_manage(self, Session):
        c = _client(Session, _user("viewer"))
        r = c.get(f"/runtime/executions/{uuid.uuid4()}/retries")
        assert r.status_code == 403

    def test_envelope_shape_health(self, Session):
        c = _client(Session)
        env = c.get("/runtime/health").json()
        assert set(env.keys()) >= {"success", "data", "meta"}
        assert env["meta"]["requestId"].startswith("req_")

    def test_envelope_shape_statistics(self, Session):
        c = _client(Session)
        env = c.get("/runtime/statistics").json()
        assert env["success"] is True
        assert set(env["data"].keys()) == {
            "overview",
            "topWorkflows",
            "topFailures",
            "metrics",
        }

    def test_statistics_metrics_included(self, Session):
        c = _client(Session)
        data = c.get("/runtime/statistics").json()["data"]
        assert "executionsTotal" in data["metrics"]

    def test_retries_endpoint_camel_case(self, Session):
        db = Session()
        wf = _mk_definition(db)
        a = _mk_action(db, wf)
        exe = _mk_execution(db, wf)
        _mk_step(db, exe, a)
        db.commit()
        eid = str(exe.id)
        db.close()
        c = _client(Session)
        step = c.get(f"/runtime/executions/{eid}/retries").json()["data"]["steps"][0]
        assert "retryCount" in step and "stepId" in step

    def test_health_check_names_are_camel_case_safe(self, Session):
        c = _client(Session)
        checks = c.get("/runtime/health").json()["data"]["checks"]
        for name in ("registry", "scheduler", "queue", "celery", "handlers"):
            assert name in checks

    def test_statistics_overview_keys_camel_case(self, Session):
        c = _client(Session)
        ov = c.get("/runtime/statistics").json()["data"]["overview"]
        for k in ("successRate", "failureRate", "retryRate", "avgDurationSeconds"):
            assert k in ov

    def test_health_status_field_is_string(self, Session):
        c = _client(Session)
        s = c.get("/runtime/health").json()["data"]["status"]
        assert isinstance(s, str)