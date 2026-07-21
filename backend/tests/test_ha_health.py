from __future__ import annotations

from app.runtime.monitoring.health import (
    STATUS_OK,
    WorkflowRuntimeHealth,
)


def test_check_includes_leader():
    r = WorkflowRuntimeHealth().check()
    assert "leader" in r["checks"]
    assert "isLeader" in r["checks"]["leader"]


def test_check_includes_lock_provider():
    r = WorkflowRuntimeHealth().check()
    assert "lockProvider" in r["checks"]
    assert r["checks"]["lockProvider"]["status"] == STATUS_OK


def test_check_includes_idempotency():
    r = WorkflowRuntimeHealth().check()
    assert "idempotency" in r["checks"]
    assert r["checks"]["idempotency"]["provider"] == "InMemoryIdempotencyStore"


def test_lock_provider_reports_class_name():
    r = WorkflowRuntimeHealth().check()
    assert r["checks"]["lockProvider"]["provider"] == "InMemoryLockProvider"


def test_leader_status_reports_provider_class_name():
    r = WorkflowRuntimeHealth().check()
    assert r["checks"]["leader"]["provider"] == "InMemoryLockProvider"


def test_overall_status_includes_new_checks():
    r = WorkflowRuntimeHealth().check()
    assert r["status"] in {"ok", "degraded", "unhealthy", "unknown"}


def test_health_returns_dict():
    r = WorkflowRuntimeHealth().check()
    assert isinstance(r, dict)
    assert set(r) >= {"status", "checks"}
