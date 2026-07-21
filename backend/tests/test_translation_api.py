"""Router-level tests for the multilingual platform (Phase 5.3)."""
from __future__ import annotations

import types
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import translations as tr_router
from app.core.exceptions import install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.audit import AuditLog
from app.models.notification import Notification, NotificationPreference
from app.models.translation import Translation, TranslationJob, TranslationLocale


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def tr_engine():
    from app.models.user import User

    Translation.__table__.c["metadata"].type = JSON()
    TranslationJob.__table__.c["metadata"].type = JSON()
    AuditLog.__table__.c["metadata"].type = JSON()
    NotificationPreference.__table__.c["quiet_hours"].type = JSON()

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    for tbl in (
        User.__table__,
        Translation.__table__,
        TranslationJob.__table__,
        TranslationLocale.__table__,
        AuditLog.__table__,
        Notification.__table__,
        NotificationPreference.__table__,
    ):
        tbl.create(eng, checkfirst=True)
    return eng


@pytest.fixture
def Session(tr_engine):
    return sessionmaker(bind=tr_engine, autoflush=False, autocommit=False, future=True)


def _fake_user(role: str, user_id: uuid.UUID | None = None):
    return types.SimpleNamespace(
        id=user_id or uuid.uuid4(),
        roles=[types.SimpleNamespace(name=role)],
        is_active=True,
        deleted_at=None,
    )


def _client(Session, user=None):
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(tr_router.router, prefix="/translations", tags=["translations"])

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    if user is not None:
        app.dependency_overrides[current_user] = lambda: user
    return TestClient(app)


def _tpayload(**overrides):
    payload = {
        "entityType": "campaign",
        "entityId": str(uuid.uuid4()),
        "locale": "hi",
        "fieldName": "title",
        "translatedValue": "",
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------- #
# Translations CRUD + envelope
# --------------------------------------------------------------------------- #


def test_create_get_update_delete_translation(Session):
    mgr = _fake_user("super_admin")
    client = _client(Session, mgr)

    body = _tpayload(translatedValue="Namaste")
    r = client.post("/translations", json=body)
    assert r.status_code == 201, r.text
    env = r.json()
    assert env["success"] is True
    assert env["meta"]["requestId"].startswith("req_")
    tid = env["data"]["id"]
    assert env["data"]["locale"] == "hi"
    assert env["data"]["status"] == "draft"

    g = client.get(f"/translations/{tid}")
    assert g.status_code == 200
    assert g.json()["data"]["translatedValue"] == "Namaste"

    u = client.patch(f"/translations/{tid}", json={"translatedValue": "Updated"})
    assert u.status_code == 200
    assert u.json()["data"]["translatedValue"] == "Updated"

    d = client.delete(f"/translations/{tid}")
    assert d.status_code == 200
    assert d.json()["data"]["deleted"] is True


def test_duplicate_translation_conflict(Session):
    client = _client(Session, _fake_user("super_admin"))
    body = _tpayload()
    r1 = client.post("/translations", json=body)
    assert r1.status_code == 201
    r2 = client.post("/translations", json=body)
    assert r2.status_code == 409


def test_permission_denied_for_viewer(Session):
    client = _client(Session, _fake_user("viewer"))
    r = client.post("/translations", json=_tpayload())
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Workflow: review, publish, reject, invalid transitions
# --------------------------------------------------------------------------- #


def _create(client, **overrides) -> str:
    r = client.post("/translations", json=_tpayload(**overrides))
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def test_review_publish_flow(Session):
    mgr = _client(Session, _fake_user("super_admin"))
    tid = _create(mgr, translatedValue="hello")

    # draft -> translated
    p = mgr.patch(f"/translations/{tid}", json={"status": "translated"})
    assert p.status_code == 200
    assert p.json()["data"]["status"] == "translated"

    # translated -> reviewed
    rv = mgr.post(f"/translations/{tid}/review")
    assert rv.status_code == 200
    assert rv.json()["data"]["status"] == "reviewed"

    # reviewed -> published
    pub = mgr.post(f"/translations/{tid}/publish")
    assert pub.status_code == 200
    assert pub.json()["data"]["status"] == "published"


def test_reject_returns_to_draft(Session):
    mgr = _client(Session, _fake_user("super_admin"))
    tid = _create(mgr, translatedValue="salut")
    mgr.patch(f"/translations/{tid}", json={"status": "translated"})
    mgr.post(f"/translations/{tid}/review")

    rj = mgr.post(f"/translations/{tid}/reject")
    assert rj.status_code == 200
    assert rj.json()["data"]["status"] == "draft"
    # reviewer bookkeeping reset is handled by service; router just proxies status


def test_invalid_transition_conflict(Session):
    mgr = _client(Session, _fake_user("super_admin"))
    tid = _create(mgr, translatedValue="x")
    # draft -> published is not allowed
    r = mgr.post(f"/translations/{tid}/publish")
    assert r.status_code == 409


# --------------------------------------------------------------------------- #
# Entity translation lookup + list pagination
# --------------------------------------------------------------------------- #


def test_entity_lookup_and_pagination(Session):
    mgr = _client(Session, _fake_user("super_admin"))
    entity_id = str(uuid.uuid4())
    for locale, field in (("hi", "title"), ("ta", "title"), ("hi", "body")):
        r = mgr.post(
            "/translations",
            json=_tpayload(entityId=entity_id, locale=locale, fieldName=field),
        )
        assert r.status_code == 201

    ents = mgr.get(f"/translations/entity/campaign/{entity_id}")
    assert ents.status_code == 200
    assert len(ents.json()["data"]) == 3

    filtered = mgr.get(f"/translations/entity/campaign/{entity_id}?locale=hi")
    assert filtered.status_code == 200
    assert len(filtered.json()["data"]) == 2

    lst = mgr.get(
        "/translations", params={"entityId": entity_id, "page": 1, "pageSize": 2}
    )
    assert lst.status_code == 200
    body = lst.json()
    assert body["pagination"]["total"] >= 3
    assert body["pagination"]["pageSize"] == 2
    assert len(body["data"]) == 2


# --------------------------------------------------------------------------- #
# Locale management
# --------------------------------------------------------------------------- #


def test_locale_lifecycle(Session):
    mgr = _client(Session, _fake_user("super_admin"))
    code = f"xx-{uuid.uuid4().hex[:4]}"

    reg = mgr.post(
        "/translations/locales",
        json={"locale": code, "displayName": "Test", "sortOrder": 5},
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["data"]["locale"] == code
    assert reg.json()["data"]["enabled"] is True

    upd = mgr.patch(
        f"/translations/locales/{code}",
        json={"displayName": "Renamed", "sortOrder": 10},
    )
    assert upd.status_code == 200
    assert upd.json()["data"]["displayName"] == "Renamed"
    assert upd.json()["data"]["sortOrder"] == 10

    dis = mgr.post(f"/translations/locales/{code}/disable")
    assert dis.status_code == 200
    assert dis.json()["data"]["enabled"] is False

    ena = mgr.post(f"/translations/locales/{code}/enable")
    assert ena.status_code == 200
    assert ena.json()["data"]["enabled"] is True

    default = mgr.post(f"/translations/locales/{code}/set-default")
    assert default.status_code == 200
    assert default.json()["data"]["defaultLocale"] is True

    lst = mgr.get("/translations/locales")
    assert lst.status_code == 200
    assert any(l["locale"] == code for l in lst.json()["data"])


# --------------------------------------------------------------------------- #
# Job lifecycle
# --------------------------------------------------------------------------- #


def _ensure_locale(client, code: str) -> None:
    """Registry may be populated by earlier tests; register on demand."""
    r = client.post(
        "/translations/locales", json={"locale": code, "displayName": code.upper()}
    )
    assert r.status_code in (201, 409), r.text


def test_job_lifecycle_and_pagination(Session):
    mgr = _client(Session, _fake_user("super_admin"))
    _ensure_locale(mgr, "hi")

    create = mgr.post(

        "/translations/jobs",
        json={
            "entityType": "campaign",
            "entityId": str(uuid.uuid4()),
            "sourceLocale": "en",
            "targetLocale": "hi",
        },
    )
    assert create.status_code == 201, create.text
    jid = create.json()["data"]["id"]
    assert create.json()["data"]["status"] == "pending"

    st = mgr.post(f"/translations/jobs/{jid}/start")
    assert st.status_code == 200
    assert st.json()["data"]["status"] == "processing"

    co = mgr.post(
        f"/translations/jobs/{jid}/complete", json={"metadata": {"chars": 42}}
    )
    assert co.status_code == 200
    assert co.json()["data"]["status"] == "completed"
    assert co.json()["data"]["metadata"]["chars"] == 42

    # completed -> cancelled is illegal
    bad = mgr.post(f"/translations/jobs/{jid}/cancel")
    assert bad.status_code == 409

    lst = mgr.get("/translations/jobs", params={"page": 1, "pageSize": 5})
    assert lst.status_code == 200
    body = lst.json()
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["pageSize"] == 5
    assert body["pagination"]["total"] >= 1


def test_job_fail_transition(Session):
    mgr = _client(Session, _fake_user("super_admin"))
    _ensure_locale(mgr, "hi")
    create = mgr.post(

        "/translations/jobs",
        json={
            "entityType": "campaign",
            "entityId": str(uuid.uuid4()),
            "sourceLocale": "en",
            "targetLocale": "hi",
        },
    )
    jid = create.json()["data"]["id"]
    mgr.post(f"/translations/jobs/{jid}/start")
    fail = mgr.post(f"/translations/jobs/{jid}/fail", json={"error": "boom"})
    assert fail.status_code == 200
    assert fail.json()["data"]["status"] == "failed"
    assert fail.json()["data"]["metadata"]["error"] == "boom"
