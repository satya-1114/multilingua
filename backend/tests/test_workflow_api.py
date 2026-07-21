"""Router-level tests for the Automation & Workflow Engine (Phase 7.3).

Isolated in-memory SQLite engine — JSONB swapped for JSON, cross-table
FKs stripped for `organizations`; workflow-internal FKs preserved.
Follows the same pattern as ``tests/test_analytics_api.py`` and
``tests/test_workflow.py``.
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

from app.api.v1 import workflow as wf_router
from app.core.exceptions import install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.workflow import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTrigger,
)


# --------------------------------------------------------------------------- #
# Engine
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


def _user(role: str):
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        roles=[types.SimpleNamespace(name=role)],
        is_active=True,
        deleted_at=None,
    )


def _client(Session, user):
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(wf_router.router, prefix="/workflows", tags=["workflows"])

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _admin(Session):
    return _client(Session, _user("super_admin"))


# --------------------------------------------------------------------------- #
# Definition CRUD + envelope
# --------------------------------------------------------------------------- #


def _wf_payload(**over):
    body = {"name": f"WF-{uuid.uuid4().hex[:6]}", "triggerType": "event"}
    body.update(over)
    return body


def test_workflow_crud_and_envelope(Session):
    c = _admin(Session)

    r = c.post("/workflows", json=_wf_payload(name="Alpha", description="d"))
    assert r.status_code == 201, r.text
    env = r.json()
    assert env["success"] is True
    assert env["meta"]["requestId"].startswith("req_")
    wid = env["data"]["id"]
    assert env["data"]["name"] == "Alpha"
    assert env["data"]["triggerType"] == "event"
    assert env["data"]["enabled"] is True

    g = c.get(f"/workflows/{wid}")
    assert g.status_code == 200
    assert g.json()["data"]["name"] == "Alpha"

    u = c.patch(f"/workflows/{wid}", json={"description": "d2", "enabled": False})
    assert u.status_code == 200
    assert u.json()["data"]["enabled"] is False
    assert u.json()["data"]["description"] == "d2"

    d = c.delete(f"/workflows/{wid}")
    assert d.status_code == 200
    assert d.json()["data"]["deleted"] is True


def test_workflow_lifecycle_enable_disable(Session):
    c = _admin(Session)
    wid = c.post("/workflows", json=_wf_payload()).json()["data"]["id"]

    r = c.post(f"/workflows/{wid}/disable")
    assert r.status_code == 200
    assert r.json()["data"]["enabled"] is False

    r = c.post(f"/workflows/{wid}/enable")
    assert r.status_code == 200
    assert r.json()["data"]["enabled"] is True


def test_workflow_list_pagination_and_filters(Session):
    c = _admin(Session)
    for i in range(4):
        c.post(
            "/workflows",
            json=_wf_payload(name=f"P-{i}", enabled=(i % 2 == 0)),
        )

    r = c.get("/workflows", params={"page": 1, "pageSize": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["pageSize"] == 2
    assert body["pagination"]["total"] >= 4
    assert len(body["data"]) == 2

    r = c.get("/workflows", params={"enabled": "true"})
    assert r.status_code == 200
    assert all(d["enabled"] for d in r.json()["data"])

    r = c.get("/workflows", params={"q": "P-1"})
    assert r.status_code == 200
    names = [d["name"] for d in r.json()["data"]]
    assert "P-1" in names


def test_workflow_create_validation_error_bad_trigger(Session):
    c = _admin(Session)
    r = c.post("/workflows", json={"name": "X", "triggerType": "bogus"})
    # Pydantic literal — 422 from FastAPI request validation.
    assert r.status_code == 422


def test_workflow_duplicate_name_conflict(Session):
    c = _admin(Session)
    r1 = c.post("/workflows", json=_wf_payload(name="DupWF"))
    assert r1.status_code == 201
    r2 = c.post("/workflows", json=_wf_payload(name="DupWF"))
    assert r2.status_code == 409


def test_workflow_rbac_denied_for_viewer_writes(Session):
    _admin(Session)  # noop
    c = _client(Session, _user("viewer"))
    r = c.post("/workflows", json=_wf_payload())
    assert r.status_code == 403


def test_workflow_rbac_viewer_can_list(Session):
    _admin(Session).post("/workflows", json=_wf_payload())
    r = _client(Session, _user("viewer")).get("/workflows")
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# Triggers
# --------------------------------------------------------------------------- #


def test_trigger_crud_and_list(Session):
    c = _admin(Session)
    wid = c.post("/workflows", json=_wf_payload()).json()["data"]["id"]

    r = c.post(
        f"/workflows/{wid}/triggers",
        json={
            "workflowDefinitionId": wid,
            "eventName": "user.created",
            "eventSource": "auth",
        },
    )
    assert r.status_code == 201, r.text
    tid = r.json()["data"]["id"]

    lst = c.get(f"/workflows/{wid}/triggers")
    assert lst.status_code == 200
    assert lst.json()["pagination"]["total"] == 1

    g = c.get(f"/workflows/triggers/{tid}")
    assert g.status_code == 200
    assert g.json()["data"]["eventName"] == "user.created"

    u = c.patch(f"/workflows/triggers/{tid}", json={"eventName": "user.updated"})
    assert u.status_code == 200
    assert u.json()["data"]["eventName"] == "user.updated"

    d = c.delete(f"/workflows/triggers/{tid}")
    assert d.status_code == 200


# --------------------------------------------------------------------------- #
# Actions + reorder
# --------------------------------------------------------------------------- #


def _make_workflow_with_actions(c, n=3):
    wid = c.post("/workflows", json=_wf_payload()).json()["data"]["id"]
    ids = []
    for i in range(1, n + 1):
        r = c.post(
            f"/workflows/{wid}/actions",
            json={
                "workflowDefinitionId": wid,
                "sequence": i,
                "actionType": "notification",
            },
        )
        assert r.status_code == 201, r.text
        ids.append(r.json()["data"]["id"])
    return wid, ids


def test_action_crud_and_get(Session):
    c = _admin(Session)
    wid, ids = _make_workflow_with_actions(c, n=1)
    aid = ids[0]

    g = c.get(f"/workflows/actions/{aid}")
    assert g.status_code == 200
    assert g.json()["data"]["sequence"] == 1

    u = c.patch(f"/workflows/actions/{aid}", json={"enabled": False})
    assert u.status_code == 200
    assert u.json()["data"]["enabled"] is False

    lst = c.get(f"/workflows/{wid}/actions")
    assert lst.status_code == 200
    assert len(lst.json()["data"]) == 1

    d = c.delete(f"/workflows/actions/{aid}")
    assert d.status_code == 200


def test_action_reorder(Session):
    c = _admin(Session)
    wid, ids = _make_workflow_with_actions(c, n=3)
    reversed_ids = list(reversed(ids))
    r = c.post(
        f"/workflows/{wid}/actions/reorder",
        json={"orderedActionIds": reversed_ids},
    )
    assert r.status_code == 200, r.text
    result = r.json()["data"]
    assert [a["id"] for a in result] == reversed_ids
    assert [a["sequence"] for a in result] == [1, 2, 3]


def test_action_reorder_length_mismatch_422(Session):
    c = _admin(Session)
    wid, ids = _make_workflow_with_actions(c, n=3)
    r = c.post(
        f"/workflows/{wid}/actions/reorder",
        json={"orderedActionIds": ids[:2]},
    )
    assert r.status_code == 422


def test_action_duplicate_sequence_conflict(Session):
    c = _admin(Session)
    wid, _ = _make_workflow_with_actions(c, n=1)
    r = c.post(
        f"/workflows/{wid}/actions",
        json={
            "workflowDefinitionId": wid,
            "sequence": 1,
            "actionType": "notification",
        },
    )
    assert r.status_code == 409


# --------------------------------------------------------------------------- #
# Executions + lifecycle
# --------------------------------------------------------------------------- #


def test_execution_start_and_transitions(Session):
    c = _admin(Session)
    wid = c.post("/workflows", json=_wf_payload()).json()["data"]["id"]

    r = c.post(
        f"/workflows/{wid}/executions",
        json={"workflowDefinitionId": wid, "triggerEvent": "manual"},
    )
    assert r.status_code == 201, r.text
    eid = r.json()["data"]["id"]
    assert r.json()["data"]["status"] == "running"

    r = c.post(f"/workflows/executions/{eid}/complete")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "completed"

    # illegal transition — completed -> anything else fails 422.
    r = c.post(f"/workflows/executions/{eid}/cancel")
    assert r.status_code == 422


def test_execution_start_disabled_workflow_rejected(Session):
    c = _admin(Session)
    wid = c.post("/workflows", json=_wf_payload()).json()["data"]["id"]
    c.post(f"/workflows/{wid}/disable")
    r = c.post(
        f"/workflows/{wid}/executions",
        json={"workflowDefinitionId": wid},
    )
    assert r.status_code == 422


def test_execution_list_with_filters(Session):
    c = _admin(Session)
    wid = c.post("/workflows", json=_wf_payload()).json()["data"]["id"]
    for _ in range(3):
        c.post(f"/workflows/{wid}/executions", json={"workflowDefinitionId": wid})

    r = c.get(f"/workflows/{wid}/executions", params={"status": "running"})
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] == 3
    assert all(x["status"] == "running" for x in body["data"])

    r = c.get(
        f"/workflows/{wid}/executions",
        params={
            "startedFrom": _iso(datetime.now(timezone.utc) - timedelta(days=1)),
        },
    )
    assert r.status_code == 200


def test_execution_get_update_delete(Session):
    c = _admin(Session)
    wid = c.post("/workflows", json=_wf_payload()).json()["data"]["id"]
    eid = c.post(
        f"/workflows/{wid}/executions", json={"workflowDefinitionId": wid}
    ).json()["data"]["id"]

    g = c.get(f"/workflows/executions/{eid}")
    assert g.status_code == 200

    u = c.patch(
        f"/workflows/executions/{eid}",
        json={"contextJson": {"k": "v"}, "metadata": {"src": "test"}},
    )
    assert u.status_code == 200
    assert u.json()["data"]["contextJson"] == {"k": "v"}

    # Cancel then delete.
    c.post(f"/workflows/executions/{eid}/cancel", json={"reason": "test"})
    d = c.delete(f"/workflows/executions/{eid}")
    assert d.status_code == 200


# --------------------------------------------------------------------------- #
# Steps + retry
# --------------------------------------------------------------------------- #


def _seeded_execution_with_action(c):
    wid, ids = _make_workflow_with_actions(c, n=1)
    eid = c.post(
        f"/workflows/{wid}/executions", json={"workflowDefinitionId": wid}
    ).json()["data"]["id"]
    return wid, eid, ids[0]


def test_step_crud_and_list(Session):
    c = _admin(Session)
    _, eid, aid = _seeded_execution_with_action(c)

    r = c.post(
        f"/workflows/executions/{eid}/steps",
        json={
            "workflowExecutionId": eid,
            "workflowActionId": aid,
            "status": "pending",
        },
    )
    assert r.status_code == 201, r.text
    sid = r.json()["data"]["id"]

    lst = c.get(f"/workflows/executions/{eid}/steps")
    assert lst.status_code == 200
    assert lst.json()["pagination"]["total"] == 1

    g = c.get(f"/workflows/steps/{sid}")
    assert g.status_code == 200


def test_step_transition_and_retry(Session):
    c = _admin(Session)
    _, eid, aid = _seeded_execution_with_action(c)
    sid = c.post(
        f"/workflows/executions/{eid}/steps",
        json={
            "workflowExecutionId": eid,
            "workflowActionId": aid,
            "status": "pending",
        },
    ).json()["data"]["id"]

    r = c.patch(f"/workflows/steps/{sid}", json={"status": "running"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "running"

    r = c.patch(
        f"/workflows/steps/{sid}",
        json={"status": "failed", "errorMessage": "boom"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "failed"

    r = c.post(f"/workflows/steps/{sid}/retry", json={"maxRetries": 3})
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["status"] == "running"
    assert body["retryCount"] == 1


def test_step_retry_only_from_failed(Session):
    c = _admin(Session)
    _, eid, aid = _seeded_execution_with_action(c)
    sid = c.post(
        f"/workflows/executions/{eid}/steps",
        json={
            "workflowExecutionId": eid,
            "workflowActionId": aid,
            "status": "pending",
        },
    ).json()["data"]["id"]

    r = c.post(f"/workflows/steps/{sid}/retry", json={"maxRetries": 3})
    assert r.status_code == 422


def test_step_delete(Session):
    c = _admin(Session)
    _, eid, aid = _seeded_execution_with_action(c)
    sid = c.post(
        f"/workflows/executions/{eid}/steps",
        json={
            "workflowExecutionId": eid,
            "workflowActionId": aid,
            "status": "pending",
        },
    ).json()["data"]["id"]
    r = c.delete(f"/workflows/steps/{sid}")
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# RBAC — execute permission
# --------------------------------------------------------------------------- #


def test_execute_permission_required_for_transitions(Session):
    admin = _admin(Session)
    wid = admin.post("/workflows", json=_wf_payload()).json()["data"]["id"]
    eid = admin.post(
        f"/workflows/{wid}/executions", json={"workflowDefinitionId": wid}
    ).json()["data"]["id"]

    viewer = _client(Session, _user("viewer"))
    r = viewer.post(f"/workflows/executions/{eid}/complete")
    assert r.status_code == 403


def test_automation_admin_can_execute(Session):
    admin = _admin(Session)
    wid = admin.post("/workflows", json=_wf_payload()).json()["data"]["id"]
    eid = admin.post(
        f"/workflows/{wid}/executions", json={"workflowDefinitionId": wid}
    ).json()["data"]["id"]

    aa = _client(Session, _user("automation_admin"))
    r = aa.post(f"/workflows/executions/{eid}/complete")
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# 404s + OpenAPI registration
# --------------------------------------------------------------------------- #


def test_get_missing_workflow_404(Session):
    c = _admin(Session)
    r = c.get(f"/workflows/{uuid.uuid4()}")
    assert r.status_code == 404


def test_openapi_registers_all_workflow_routes(Session):
    c = _admin(Session)
    spec = c.get("/openapi.json").json()
    paths = set(spec["paths"].keys())
    expected = {
        "/workflows",
        "/workflows/{workflow_id}",
        "/workflows/{workflow_id}/enable",
        "/workflows/{workflow_id}/disable",
        "/workflows/{workflow_id}/triggers",
        "/workflows/triggers/{trigger_id}",
        "/workflows/{workflow_id}/actions",
        "/workflows/actions/{action_id}",
        "/workflows/{workflow_id}/actions/reorder",
        "/workflows/{workflow_id}/executions",
        "/workflows/executions/{execution_id}",
        "/workflows/executions/{execution_id}/complete",
        "/workflows/executions/{execution_id}/fail",
        "/workflows/executions/{execution_id}/cancel",
        "/workflows/executions/{execution_id}/steps",
        "/workflows/steps/{step_id}",
        "/workflows/steps/{step_id}/retry",
    }
    missing = expected - paths
    assert not missing, f"missing OpenAPI paths: {sorted(missing)}"
