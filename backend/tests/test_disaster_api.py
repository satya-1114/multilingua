"""Router-level tests for the Disaster module.

Builds a minimal FastAPI app that mounts only the disasters router (plus the
project's exception handlers) so the pre-existing SQLite/JSONB issues in
other modules don't block us. Uses the same test-only column-type shim as
``test_disaster.py`` / ``test_volunteer_api.py``.
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
from app.models.disaster import Disaster, DisasterAssignment, DisasterAttachment
from app.models.volunteer import Volunteer, VolunteerTask


# --------------------------------------------------------------------------- #
# In-memory DB & test app
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def dis_engine():
    from app.models.audit import AuditLog
    from app.models.campaign import Campaign
    from app.models.notification import Notification
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
def Session(dis_engine):
    return sessionmaker(
        bind=dis_engine, autoflush=False, autocommit=False, future=True
    )


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
    app.include_router(
        disasters_router.router, prefix="/disasters", tags=["disasters"]
    )

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
    """Insert a volunteer row directly (the volunteers router isn't mounted here)."""
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


# --------------------------------------------------------------------------- #
# Disaster routes
# --------------------------------------------------------------------------- #


def test_create_get_list_and_update_disaster(Session):
    manager = _fake_user("campaign_manager")
    client = _build_client(Session, manager)
    payload = {
        "title": "Flood in Zone 3",
        "disasterType": "flood",
        "severity": "high",
        "city": "Chennai",
    }
    r = client.post("/disasters", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["success"] is True
    did = body["data"]["id"]
    assert body["data"]["status"] == "reported"
    assert body["data"]["disasterType"] == "flood"

    # GET one
    g = client.get(f"/disasters/{did}")
    assert g.status_code == 200
    assert g.json()["data"]["title"] == "Flood in Zone 3"

    # PATCH
    u = client.patch(f"/disasters/{did}", json={"description": "Rising water"})
    assert u.status_code == 200
    assert u.json()["data"]["description"] == "Rising water"

    # List + filter
    lst = client.get("/disasters", params={"disasterType": "flood", "page": 1, "pageSize": 10})
    assert lst.status_code == 200
    assert lst.json()["pagination"]["total"] >= 1


def test_disaster_permission_denied(Session):
    viewer = _fake_user("viewer")
    client = _build_client(Session, viewer)
    r = client.post(
        "/disasters", json={"title": "X", "disasterType": "flood", "severity": "low"}
    )
    assert r.status_code == 403


def test_disaster_state_machine_transitions(Session):
    manager = _fake_user("campaign_manager")
    client = _build_client(Session, manager)
    did = client.post(
        "/disasters",
        json={"title": "Fire", "disasterType": "fire", "severity": "critical"},
    ).json()["data"]["id"]

    assert client.post(f"/disasters/{did}/verify").json()["data"]["status"] == "verified"
    assert client.post(f"/disasters/{did}/activate").json()["data"]["status"] == "active"
    assert client.post(f"/disasters/{did}/contain").json()["data"]["status"] == "contained"
    r = client.post(f"/disasters/{did}/resolve")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "resolved"
    assert r.json()["data"]["resolvedAt"] is not None
    # Reopen is only permitted from resolved
    assert client.post(f"/disasters/{did}/reopen").json()["data"]["status"] == "active"


def test_disaster_illegal_transition_returns_409(Session):
    manager = _fake_user("campaign_manager")
    client = _build_client(Session, manager)
    did = client.post(
        "/disasters",
        json={"title": "Q", "disasterType": "flood", "severity": "low"},
    ).json()["data"]["id"]
    # reported → active is illegal (must go via verified)
    r = client.post(f"/disasters/{did}/activate")
    assert r.status_code == 409


# --------------------------------------------------------------------------- #
# Assignment routes
# --------------------------------------------------------------------------- #


def test_assignment_full_lifecycle(Session):
    manager = _fake_user("campaign_manager")
    mclient = _build_client(Session, manager)

    did = mclient.post(
        "/disasters",
        json={"title": "Cyclone", "disasterType": "cyclone", "severity": "high"},
    ).json()["data"]["id"]
    # Move disaster to a non-terminal state
    mclient.post(f"/disasters/{did}/verify")

    vuser_id = uuid.uuid4()
    vid = str(_create_volunteer(Session, user_id=vuser_id))

    # Create assignment
    ca = mclient.post(f"/disasters/{did}/assignments", json={"volunteerId": vid, "role": "lead"})
    assert ca.status_code == 201, ca.text
    aid = ca.json()["data"]["id"]
    assert ca.json()["data"]["status"] == "assigned"

    # Duplicate assignment for same volunteer → 409
    dup = mclient.post(f"/disasters/{did}/assignments", json={"volunteerId": vid})
    assert dup.status_code == 409

    # Edit metadata
    ed = mclient.patch(f"/disasters/assignments/{aid}", json={"notes": "on site"})
    assert ed.status_code == 200
    assert ed.json()["data"]["notes"] == "on site"

    # Volunteer drives status: accepted → in_progress
    vclient = _build_client(Session, _fake_user("volunteer", user_id=vuser_id))
    for target in ("accepted", "in_progress"):
        s = vclient.patch(f"/disasters/assignments/{aid}/status", json={"status": target})
        assert s.status_code == 200, s.text
        assert s.json()["data"]["status"] == target

    # Complete
    done = vclient.post(f"/disasters/assignments/{aid}/complete")
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "completed"
    assert done.json()["data"]["completedAt"] is not None

    # List
    lst = mclient.get(f"/disasters/{did}/assignments")
    assert lst.status_code == 200
    assert any(a["id"] == aid for a in lst.json()["data"])


def test_assignment_reassign_and_cancel(Session):
    manager = _fake_user("campaign_manager")
    mclient = _build_client(Session, manager)

    did = mclient.post(
        "/disasters",
        json={"title": "Quake", "disasterType": "earthquake", "severity": "high"},
    ).json()["data"]["id"]
    mclient.post(f"/disasters/{did}/verify")

    v1 = str(_create_volunteer(Session))
    v2 = str(_create_volunteer(Session))

    aid = mclient.post(
        f"/disasters/{did}/assignments", json={"volunteerId": v1}
    ).json()["data"]["id"]

    r = mclient.post(f"/disasters/assignments/{aid}/reassign", json={"volunteerId": v2})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["volunteerId"] == v2

    # Cancel via DELETE
    c = mclient.delete(f"/disasters/assignments/{aid}")
    assert c.status_code == 200
    assert c.json()["data"]["status"] == "cancelled"


def test_assignment_volunteer_cannot_act_on_other(Session):
    manager = _fake_user("campaign_manager")
    mclient = _build_client(Session, manager)
    did = mclient.post(
        "/disasters",
        json={"title": "H", "disasterType": "heatwave", "severity": "medium"},
    ).json()["data"]["id"]
    mclient.post(f"/disasters/{did}/verify")

    vuser = uuid.uuid4()
    vid = str(_create_volunteer(Session, user_id=vuser))
    aid = mclient.post(
        f"/disasters/{did}/assignments", json={"volunteerId": vid}
    ).json()["data"]["id"]

    other = _build_client(Session, _fake_user("volunteer", user_id=uuid.uuid4()))
    r = other.patch(f"/disasters/assignments/{aid}/status", json={"status": "accepted"})
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Attachment routes  (metadata only)
# --------------------------------------------------------------------------- #


def test_attachment_create_list_and_delete(Session):
    manager = _fake_user("campaign_manager")
    client = _build_client(Session, manager)
    did = client.post(
        "/disasters",
        json={"title": "Landslide", "disasterType": "landslide", "severity": "high"},
    ).json()["data"]["id"]

    c = client.post(
        f"/disasters/{did}/attachments",
        json={
            "kind": "image",
            "fileName": "site.jpg",
            "fileUrl": "https://cdn.example.com/site.jpg",
            "contentType": "image/jpeg",
            "sizeBytes": 12345,
        },
    )
    assert c.status_code == 201, c.text
    xid = c.json()["data"]["id"]
    assert c.json()["data"]["fileName"] == "site.jpg"

    lst = client.get(f"/disasters/{did}/attachments")
    assert lst.status_code == 200
    assert any(a["id"] == xid for a in lst.json()["data"])

    d = client.delete(f"/disasters/attachments/{xid}")
    assert d.status_code == 200
    assert d.json()["data"]["deleted"] is True
