"""Router-level tests for volunteers & tasks.

Builds a minimal FastAPI app that mounts only the volunteers/tasks routers
(plus the project's exception handlers) so the pre-existing SQLite / JSONB
issues in other modules don't block us. Uses the same test-only column-type
shim as ``test_volunteer.py``.
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

from app.api.v1 import tasks as tasks_router
from app.api.v1 import volunteers as volunteers_router
from app.core.exceptions import install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.volunteer import Volunteer, VolunteerTask


# --------------------------------------------------------------------------- #
# In-memory DB & test app
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def vol_engine():
    from app.models.audit import AuditLog
    from app.models.campaign import Campaign
    from app.models.notification import Notification
    from app.models.organization import Organization
    from app.models.user import User

    for col_name in ("languages", "skills"):
        Volunteer.__table__.c[col_name].type = JSON()
    Campaign.__table__.c["channels"].type = JSON()
    AuditLog.__table__.c["metadata"].type = JSON()

    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True
    )
    for tbl in (
        User.__table__,
        Organization.__table__,
        Campaign.__table__,
        Volunteer.__table__,
        VolunteerTask.__table__,
        Notification.__table__,
        AuditLog.__table__,
    ):
        tbl.create(eng, checkfirst=True)
    return eng


@pytest.fixture
def Session(vol_engine):
    return sessionmaker(bind=vol_engine, autoflush=False, autocommit=False, future=True)


def _fake_user(role: str, user_id: uuid.UUID | None = None):
    return types.SimpleNamespace(
        id=user_id or uuid.uuid4(),
        roles=[types.SimpleNamespace(name=role)],
        is_active=True,
        deleted_at=None,
    )


def _build_client(Session, user):
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(volunteers_router.router, prefix="/volunteers", tags=["volunteers"])
    app.include_router(tasks_router.router, prefix="/tasks", tags=["tasks"])

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Volunteer routes
# --------------------------------------------------------------------------- #


def test_create_and_get_volunteer(Session):
    manager = _fake_user("campaign_manager")
    client = _build_client(Session, manager)
    user_id = uuid.uuid4()
    payload = {
        "userId": str(user_id),
        "languages": ["en", "hi"],
        "skills": ["first-aid"],
        "availability": "Weekends",
        "emergencyContact": {"name": "Kin", "phone": "999", "relation": "sibling"},
    }
    r = client.post("/volunteers", json=payload)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body["success"] is True
    vid = body["data"]["id"]
    assert body["data"]["userId"] == str(user_id)
    assert body["data"]["emergencyContact"]["name"] == "Kin"

    # Duplicate → 409
    r2 = client.post("/volunteers", json=payload)
    assert r2.status_code == 409

    # GET one
    g = client.get(f"/volunteers/{vid}")
    assert g.status_code == 200
    assert g.json()["data"]["status"] == "available"

    # List
    lst = client.get("/volunteers", params={"page": 1, "pageSize": 10})
    assert lst.status_code == 200
    assert lst.json()["pagination"]["total"] >= 1


def test_volunteer_permission_denied(Session):
    viewer = _fake_user("viewer")
    client = _build_client(Session, viewer)
    r = client.get("/volunteers")
    assert r.status_code == 403


def test_update_activate_deactivate_and_org(Session):
    manager = _fake_user("campaign_manager")
    client = _build_client(Session, manager)
    r = client.post("/volunteers", json={"userId": str(uuid.uuid4()), "languages": []})
    vid = r.json()["data"]["id"]

    u = client.patch(f"/volunteers/{vid}", json={"availability": "Full-time"})
    assert u.status_code == 200
    assert u.json()["data"]["availability"] == "Full-time"

    d = client.post(f"/volunteers/{vid}/deactivate")
    assert d.status_code == 200
    assert d.json()["data"]["status"] == "inactive"

    a = client.post(f"/volunteers/{vid}/activate")
    assert a.json()["data"]["status"] == "available"

    org_id = str(uuid.uuid4())
    o = client.post(f"/volunteers/{vid}/organization", json={"organizationId": org_id})
    assert o.status_code == 200
    assert o.json()["data"]["organizationId"] == org_id


# --------------------------------------------------------------------------- #
# Task routes
# --------------------------------------------------------------------------- #


def test_task_full_lifecycle(Session):
    manager = _fake_user("campaign_manager")
    mclient = _build_client(Session, manager)

    volunteer_user_id = uuid.uuid4()
    r = mclient.post("/volunteers", json={"userId": str(volunteer_user_id)})
    vid = r.json()["data"]["id"]

    # Manager creates a task
    due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    ct = mclient.post(
        "/tasks",
        json={
            "volunteerId": vid,
            "title": "Distribute flyers",
            "priority": "high",
            "dueAt": due,
        },
    )
    assert ct.status_code == 201, ct.text
    tid = ct.json()["data"]["id"]
    assert ct.json()["data"]["status"] == "pending"

    # Manager edits it
    ed = mclient.patch(f"/tasks/{tid}", json={"title": "Distribute flyers v2"})
    assert ed.status_code == 200
    assert ed.json()["data"]["title"] == "Distribute flyers v2"

    # Volunteer accepts → in_progress → complete
    vuser = _fake_user("volunteer", user_id=volunteer_user_id)
    vclient = _build_client(Session, vuser)

    for target in ("accepted", "in_progress"):
        s = vclient.patch(f"/tasks/{tid}/status", json={"status": target})
        assert s.status_code == 200, s.text
        assert s.json()["data"]["status"] == target

    done = vclient.post(f"/tasks/{tid}/complete")
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "completed"
    assert done.json()["data"]["completedAt"] is not None

    # /tasks/mine returns this task
    mine = vclient.get("/tasks/mine")
    assert mine.status_code == 200
    assert any(t["id"] == tid for t in mine.json()["data"])

    # Manager list w/ filter
    lst = mclient.get("/tasks", params={"volunteerId": vid})
    assert lst.status_code == 200
    assert lst.json()["pagination"]["total"] >= 1


def test_task_illegal_transition_and_cancel(Session):
    manager = _fake_user("campaign_manager")
    mclient = _build_client(Session, manager)

    vuid = uuid.uuid4()
    vid = mclient.post("/volunteers", json={"userId": str(vuid)}).json()["data"]["id"]
    tid = mclient.post(
        "/tasks", json={"volunteerId": vid, "title": "Task"}
    ).json()["data"]["id"]

    # Volunteer cannot jump pending → completed
    vclient = _build_client(Session, _fake_user("volunteer", user_id=vuid))
    bad = vclient.patch(f"/tasks/{tid}/status", json={"status": "completed"})
    assert bad.status_code == 409

    # A different volunteer cannot act on someone else's task
    other = _build_client(Session, _fake_user("volunteer", user_id=uuid.uuid4()))
    other_resp = other.patch(f"/tasks/{tid}/status", json={"status": "accepted"})
    assert other_resp.status_code == 403

    # Manager cancels
    cancel = mclient.delete(f"/tasks/{tid}")
    assert cancel.status_code == 200
    assert cancel.json()["data"]["status"] == "cancelled"


def test_task_past_due_rejected(Session):
    manager = _fake_user("campaign_manager")
    mclient = _build_client(Session, manager)
    vid = mclient.post(
        "/volunteers", json={"userId": str(uuid.uuid4())}
    ).json()["data"]["id"]

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    r = mclient.post(
        "/tasks",
        json={"volunteerId": vid, "title": "late", "dueAt": past},
    )
    assert r.status_code == 422


def test_reassign_task(Session):
    manager = _fake_user("campaign_manager")
    mclient = _build_client(Session, manager)
    v1 = mclient.post("/volunteers", json={"userId": str(uuid.uuid4())}).json()["data"]["id"]
    v2 = mclient.post("/volunteers", json={"userId": str(uuid.uuid4())}).json()["data"]["id"]
    tid = mclient.post("/tasks", json={"volunteerId": v1, "title": "T"}).json()["data"]["id"]
    r = mclient.post(f"/tasks/{tid}/assign", json={"volunteerId": v2})
    assert r.status_code == 200
    assert r.json()["data"]["volunteerId"] == v2
