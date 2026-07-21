"""Integration tests for the Disaster → Notifications / Audit / Search pipelines.

Uses the same in-memory SQLite + column-shim strategy as test_disaster_api.py
and asserts the side-effects of the disaster router: notifications created,
audit rows written, and events emitted via the isolated `disaster_events`
helpers. Also exercises the search-scope registration for disaster and
assignment.
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

from app.api.v1 import disasters as disasters_router
from app.core.exceptions import install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.audit import AuditLog
from app.models.disaster import Disaster, DisasterAssignment, DisasterAttachment
from app.models.notification import Notification
from app.models.volunteer import Volunteer, VolunteerTask
from app.services import disaster_events, search as search_service


@pytest.fixture(scope="module")
def evt_engine():
    from app.models.campaign import Campaign
    from app.models.organization import Organization
    from app.models.user import User

    for col_name in ("languages", "skills"):
        Volunteer.__table__.c[col_name].type = JSON()
    Campaign.__table__.c["channels"].type = JSON()
    AuditLog.__table__.c["metadata"].type = JSON()
    Disaster.__table__.c["metadata"].type = JSON()

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
        Disaster.__table__,
        DisasterAssignment.__table__,
        DisasterAttachment.__table__,
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
    app.include_router(disasters_router.router, prefix="/disasters", tags=["disasters"])

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app)


def _create_volunteer(Session, user_id: uuid.UUID | None = None) -> uuid.UUID:
    from app.services import volunteer as vsvc

    s = Session()
    try:
        v = vsvc.create_volunteer(
            s,
            roles=("campaign_manager",),
            payload={
                "userId": user_id or uuid.uuid4(),
                "languages": ["en"],
                "skills": ["outreach"],
            },
        )
        return v.id
    finally:
        s.close()


def _notifs(Session, user_id):
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


def _audits(Session, module: str):
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
# Disaster lifecycle → notifications + audit
# --------------------------------------------------------------------------- #


def test_disaster_lifecycle_emits_notifications_and_audit(Session):
    manager = _fake_user("campaign_manager")
    client = _client(Session, manager)

    r = client.post(
        "/disasters",
        json={"title": "Flood A", "disasterType": "flood", "severity": "high"},
    )
    did = r.json()["data"]["id"]

    # Reporter (manager) got the "disaster reported" notification.
    reporter_titles = [n.title for n in _notifs(Session, manager.id)]
    assert any("reported" in t.lower() for t in reporter_titles)

    # Drive verify → active → resolved
    client.post(f"/disasters/{did}/verify")
    client.post(f"/disasters/{did}/activate")
    client.post(f"/disasters/{did}/resolve")

    titles = [n.title.lower() for n in _notifs(Session, manager.id)]
    assert any("verified" in t for t in titles)
    assert any("active" in t for t in titles)
    assert any("resolved" in t for t in titles)

    actions = [a.action for a in _audits(Session, "disaster")]
    for act in ("create", "verify", "activate", "resolve"):
        assert act in actions, f"missing audit action {act}: {actions}"


# --------------------------------------------------------------------------- #
# Assignment lifecycle → notifications + audit
# --------------------------------------------------------------------------- #


def test_assignment_assign_reassign_complete_events(Session):
    manager = _fake_user("campaign_manager")
    mclient = _client(Session, manager)

    did = mclient.post(
        "/disasters",
        json={"title": "Cyclone B", "disasterType": "cyclone", "severity": "high"},
    ).json()["data"]["id"]
    mclient.post(f"/disasters/{did}/verify")

    u1, u2 = uuid.uuid4(), uuid.uuid4()
    v1 = str(_create_volunteer(Session, user_id=u1))
    v2 = str(_create_volunteer(Session, user_id=u2))

    aid = mclient.post(
        f"/disasters/{did}/assignments", json={"volunteerId": v1, "role": "lead"}
    ).json()["data"]["id"]

    # First volunteer notified about assignment.
    assert any("assign" in n.title.lower() for n in _notifs(Session, u1))

    # Reassign to v2 → both notified.
    r = mclient.post(f"/disasters/assignments/{aid}/reassign", json={"volunteerId": v2})
    assert r.status_code == 200
    assert any("reassign" in n.title.lower() for n in _notifs(Session, u2))
    assert any("reassign" in n.title.lower() for n in _notifs(Session, u1))

    # Complete via volunteer.
    vclient = _client(Session, _fake_user("volunteer", user_id=u2))
    vclient.patch(f"/disasters/assignments/{aid}/status", json={"status": "accepted"})
    vclient.patch(f"/disasters/assignments/{aid}/status", json={"status": "in_progress"})
    done = vclient.post(f"/disasters/assignments/{aid}/complete")
    assert done.status_code == 200
    assert any("complet" in n.title.lower() for n in _notifs(Session, u2))

    actions = [a.action for a in _audits(Session, "assignment")]
    for act in ("assign", "reassign", "complete"):
        assert act in actions, f"missing assignment audit action {act}: {actions}"


def test_assignment_cancel_notifies_and_audits(Session):
    manager = _fake_user("campaign_manager")
    mclient = _client(Session, manager)
    did = mclient.post(
        "/disasters",
        json={"title": "Heat C", "disasterType": "heatwave", "severity": "medium"},
    ).json()["data"]["id"]
    mclient.post(f"/disasters/{did}/verify")

    vu = uuid.uuid4()
    vid = str(_create_volunteer(Session, user_id=vu))
    aid = mclient.post(
        f"/disasters/{did}/assignments", json={"volunteerId": vid}
    ).json()["data"]["id"]

    c = mclient.delete(f"/disasters/assignments/{aid}")
    assert c.status_code == 200

    assert any("cancel" in n.title.lower() for n in _notifs(Session, vu))
    actions = [a.action for a in _audits(Session, "assignment")]
    assert "cancel" in actions


# --------------------------------------------------------------------------- #
# Attachment audit
# --------------------------------------------------------------------------- #


def test_attachment_metadata_audits(Session):
    manager = _fake_user("campaign_manager")
    client = _client(Session, manager)
    did = client.post(
        "/disasters",
        json={"title": "Landslide D", "disasterType": "landslide", "severity": "high"},
    ).json()["data"]["id"]

    xid = client.post(
        f"/disasters/{did}/attachments",
        json={
            "kind": "image",
            "fileName": "s.jpg",
            "fileUrl": "https://x/s.jpg",
            "contentType": "image/jpeg",
            "sizeBytes": 10,
        },
    ).json()["data"]["id"]

    client.delete(f"/disasters/attachments/{xid}")

    actions = [a.action for a in _audits(Session, "attachment")]
    assert "create" in actions
    assert "delete" in actions


# --------------------------------------------------------------------------- #
# Event helpers isolation
# --------------------------------------------------------------------------- #


def test_disaster_events_swallow_notification_failures(Session, monkeypatch):
    """A notification failure must never bubble out of an event emitter."""
    from app.services import notifications as notif

    def _boom(*a, **kw):
        raise RuntimeError("notify down")

    monkeypatch.setattr(notif, "create", _boom)

    s = Session()
    try:
        d = Disaster(
            title="Silent",
            disaster_type="flood",
            severity="low",
            status="reported",
            created_by_user_id=uuid.uuid4(),
        )
        s.add(d)
        s.commit()
        # Should NOT raise.
        disaster_events.disaster_reported(s, d)
        disaster_events.disaster_verified(s, d)
    finally:
        s.close()


# --------------------------------------------------------------------------- #
# Search-scope registration
# --------------------------------------------------------------------------- #


def test_search_scopes_registered():
    assert "disaster" in search_service.SCOPE_PERMISSIONS
    assert "assignment" in search_service.SCOPE_PERMISSIONS
    assert search_service.SCOPE_PERMISSIONS["disaster"] == "disaster:view"
    assert search_service.SCOPE_PERMISSIONS["assignment"] == "assignment:view"
    assert "disaster" in search_service._HANDLERS
    assert "assignment" in search_service._HANDLERS


def test_search_disasters_finds_by_title(Session):
    manager = _fake_user("campaign_manager")
    client = _client(Session, manager)
    client.post(
        "/disasters",
        json={"title": "UniqueSearchQuake", "disasterType": "earthquake", "severity": "high"},
    )
    s = Session()
    try:
        res = search_service.search(
            s,
            q="UniqueSearchQuake",
            permissions={"disaster:view"},
            scopes=["disaster"],
        )
        titles = [h["title"] for h in res["results"]]
        assert "UniqueSearchQuake" in titles
    finally:
        s.close()
