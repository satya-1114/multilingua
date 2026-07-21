"""Integration tests for the Volunteer → Notifications / Audit pipelines.

Same in-memory SQLite + column-shim strategy as `test_volunteer_api.py`,
extended to also create the `notifications` and `audit_logs` tables so we
can assert side-effects of the volunteer service.
"""
from __future__ import annotations

import types
import uuid

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
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.volunteer import Volunteer, VolunteerTask


@pytest.fixture(scope="module")
def evt_engine():
    from app.models.campaign import Campaign
    from app.models.organization import Organization
    from app.models.user import User

    for col_name in ("languages", "skills"):
        Volunteer.__table__.c[col_name].type = JSON()
    Campaign.__table__.c["channels"].type = JSON()
    AuditLog.__table__.c["metadata"].type = JSON()

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
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
def Session(evt_engine):
    return sessionmaker(bind=evt_engine, autoflush=False, autocommit=False, future=True)


def _fake_user(role: str, user_id: uuid.UUID | None = None):
    return types.SimpleNamespace(
        id=user_id or uuid.uuid4(),
        roles=[types.SimpleNamespace(name=role)],
        is_active=True,
        deleted_at=None,
    )


def _client(Session, user):
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


def _notifs(Session, user_id: uuid.UUID) -> list[Notification]:
    s = Session()
    try:
        return (
            s.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.asc())
            .all()
        )
    finally:
        s.close()


def _audits(Session, module: str) -> list[AuditLog]:
    s = Session()
    try:
        return (
            s.query(AuditLog)
            .filter(AuditLog.module == module)
            .order_by(AuditLog.created_at.asc())
            .all()
        )
    finally:
        s.close()


# --------------------------------------------------------------------------- #
# Volunteer lifecycle events
# --------------------------------------------------------------------------- #


def test_volunteer_activate_deactivate_emits_notifications_and_audit(Session):
    manager = _fake_user("campaign_manager")
    client = _client(Session, manager)

    volunteer_user_id = uuid.uuid4()
    r = client.post("/volunteers", json={"userId": str(volunteer_user_id)})
    vid = r.json()["data"]["id"]

    # Fresh profile defaults to `available` — no lifecycle notification yet.
    assert _notifs(Session, volunteer_user_id) == []

    client.post(f"/volunteers/{vid}/deactivate")
    client.post(f"/volunteers/{vid}/activate")

    titles = [n.title for n in _notifs(Session, volunteer_user_id)]
    assert any("deactivated" in t.lower() for t in titles)
    assert any("active" in t.lower() for t in titles)

    # Audit: at least one create + zero-or-more updates on `volunteer` module.
    modules = [a.action for a in _audits(Session, "volunteer")]
    assert "create" in modules


# --------------------------------------------------------------------------- #
# Task lifecycle events
# --------------------------------------------------------------------------- #


def test_task_assign_complete_emits_notifications_and_audit(Session):
    manager = _fake_user("campaign_manager")
    mclient = _client(Session, manager)

    volunteer_user_id = uuid.uuid4()
    vid = mclient.post(
        "/volunteers", json={"userId": str(volunteer_user_id)}
    ).json()["data"]["id"]

    # Create → notify volunteer
    tid = mclient.post(
        "/tasks", json={"volunteerId": vid, "title": "Handout"}
    ).json()["data"]["id"]

    inbox = _notifs(Session, volunteer_user_id)
    assert any("New task" in n.title for n in inbox)
    assert all(n.category == "volunteer" for n in inbox)

    # Act as the volunteer to progress → completed
    vclient = _client(Session, _fake_user("volunteer", user_id=volunteer_user_id))
    vclient.patch(f"/tasks/{tid}/status", json={"status": "accepted"})
    vclient.patch(f"/tasks/{tid}/status", json={"status": "in_progress"})
    vclient.post(f"/tasks/{tid}/complete")

    # Volunteer notified about completion
    vol_titles = [n.title for n in _notifs(Session, volunteer_user_id)]
    assert any("completed" in t.lower() for t in vol_titles)

    # Creator (manager) also notified about completion
    mgr_inbox = _notifs(Session, manager.id)
    assert any("completed" in n.title.lower() for n in mgr_inbox)

    # Audit trail: create + complete
    actions = [a.action for a in _audits(Session, "task")]
    assert "create" in actions
    assert "complete" in actions


def test_task_reassign_notifies_both_parties_and_audits(Session):
    manager = _fake_user("campaign_manager")
    mclient = _client(Session, manager)

    u1, u2 = uuid.uuid4(), uuid.uuid4()
    v1 = mclient.post("/volunteers", json={"userId": str(u1)}).json()["data"]["id"]
    v2 = mclient.post("/volunteers", json={"userId": str(u2)}).json()["data"]["id"]
    tid = mclient.post("/tasks", json={"volunteerId": v1, "title": "T"}).json()["data"]["id"]

    r = mclient.post(f"/tasks/{tid}/assign", json={"volunteerId": v2})
    assert r.status_code == 200

    assert any("reassigned to you" in n.title.lower() for n in _notifs(Session, u2))
    assert any("reassigned" in n.title.lower() for n in _notifs(Session, u1))

    actions = [a.action for a in _audits(Session, "task")]
    assert "reassign" in actions


def test_task_cancel_notifies_volunteer_and_audits(Session):
    manager = _fake_user("campaign_manager")
    mclient = _client(Session, manager)

    vu = uuid.uuid4()
    vid = mclient.post("/volunteers", json={"userId": str(vu)}).json()["data"]["id"]
    tid = mclient.post("/tasks", json={"volunteerId": vid, "title": "X"}).json()["data"]["id"]

    r = mclient.delete(f"/tasks/{tid}")
    assert r.status_code == 200

    assert any("cancelled" in n.title.lower() for n in _notifs(Session, vu))
    actions = [a.action for a in _audits(Session, "task")]
    assert "cancel" in actions
