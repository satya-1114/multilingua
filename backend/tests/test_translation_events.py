"""Integration tests for Phase 5.4 — translation notifications, audit,
search registration, and failure isolation."""
from __future__ import annotations

import types
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import translations as tr_router
from app.core.exceptions import install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.audit import AuditLog
from app.models.notification import Notification, NotificationPreference
from app.models.translation import Translation, TranslationJob, TranslationLocale
from app.services import search as search_svc
from app.services import translation_events


@pytest.fixture(scope="module")
def engine():
    from app.models.user import User

    for tbl_cls in (Translation, TranslationJob):
        tbl_cls.__table__.c["metadata"].type = JSON()
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
def Session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _user(role: str = "super_admin"):
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        roles=[types.SimpleNamespace(name=role)],
        is_active=True,
        deleted_at=None,
    )


def _client(Session, user):
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
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app)


def _payload(**over):
    p = {
        "entityType": "campaign",
        "entityId": str(uuid.uuid4()),
        "locale": "hi",
        "fieldName": "title",
        "translatedValue": "Namaste",
    }
    p.update(over)
    return p


# --------------------------------------------------------------------------- #
# Notification emission
# --------------------------------------------------------------------------- #


def test_translation_create_emits_notification_and_audit(Session):
    user = _user()
    client = _client(Session, user)
    r = client.post("/translations", json=_payload())
    assert r.status_code == 201

    with Session() as s:
        notifs = list(s.scalars(select(Notification)))
        audits = list(s.scalars(select(AuditLog)))
    assert any(n.category == "translation" and "created" in n.title.lower() for n in notifs)
    assert any(a.module == "translation" and a.action == "create" for a in audits)


def test_publish_flow_emits_events(Session):
    user = _user()
    client = _client(Session, user)
    tid = client.post("/translations", json=_payload(translatedValue="hello")).json()["data"]["id"]
    assert client.patch(f"/translations/{tid}", json={"status": "translated"}).status_code == 200
    assert client.post(f"/translations/{tid}/review").status_code == 200
    assert client.post(f"/translations/{tid}/publish").status_code == 200

    with Session() as s:
        actions = {a.action for a in s.scalars(select(AuditLog)) if a.module == "translation"}
        titles = " ".join(n.title.lower() for n in s.scalars(select(Notification)))
    assert {"create", "update", "review", "publish"}.issubset(actions)
    assert "published" in titles and ("reviewed" in titles or "approved" in titles)


def test_locale_lifecycle_emits_events(Session):
    user = _user()
    client = _client(Session, user)
    assert client.post("/translations/locales", json={"locale": "ta", "displayName": "Tamil"}).status_code == 201
    assert client.post("/translations/locales/ta/disable").status_code == 200
    assert client.post("/translations/locales/ta/enable").status_code == 200

    with Session() as s:
        actions = {a.action for a in s.scalars(select(AuditLog)) if a.module == "translation_locale"}
    assert {"register", "enable", "disable"}.issubset(actions)


def test_job_lifecycle_emits_events(Session):
    user = _user()
    client = _client(Session, user)
    # Register target locale first
    client.post("/translations/locales", json={"locale": "te", "displayName": "Telugu"})
    body = {
        "entityType": "campaign",
        "entityId": str(uuid.uuid4()),
        "sourceLocale": "en",
        "targetLocale": "te",
    }
    r = client.post("/translations/jobs", json=body)
    assert r.status_code == 201, r.text
    jid = r.json()["data"]["id"]
    assert client.post(f"/translations/jobs/{jid}/start").status_code == 200
    assert client.post(f"/translations/jobs/{jid}/complete", json={}).status_code == 200

    with Session() as s:
        actions = {a.action for a in s.scalars(select(AuditLog)) if a.module == "translation_job"}
    assert {"create", "start", "complete"}.issubset(actions)


# --------------------------------------------------------------------------- #
# Notification failure isolation
# --------------------------------------------------------------------------- #


def test_notification_failure_does_not_break_create(Session, monkeypatch):
    from app.services import notifications as notif_service

    def boom(*a, **kw):
        raise RuntimeError("notification down")

    user = _user()
    client = _client(Session, user)
    # Ensure locale exists (may already be registered by earlier tests).
    client.post("/translations/locales", json={"locale": "hi", "displayName": "Hindi"})
    monkeypatch.setattr(notif_service, "create", boom)
    r = client.post("/translations", json=_payload(fieldName="body"))
    assert r.status_code == 201


# --------------------------------------------------------------------------- #
# Search registration
# --------------------------------------------------------------------------- #


def test_search_registers_translation_scope():
    assert "translation" in search_svc._HANDLERS
    assert search_svc.SCOPE_PERMISSIONS.get("translation") == "translation:view"


def test_search_translations_returns_hits(Session):
    user = _user()
    client = _client(Session, user)
    client.post("/translations", json=_payload(translatedValue="findable"))

    with Session() as s:
        out = search_svc._search_translations(s, "campaign", None, 10)
    assert any(h["scope"] == "translation" for h in out)


# --------------------------------------------------------------------------- #
# Event helper isolation from ORM state
# --------------------------------------------------------------------------- #


def test_event_helper_swallows_bad_session():
    class BadSession:
        def rollback(self):
            pass

    row = types.SimpleNamespace(
        entity_type="campaign",
        entity_id=uuid.uuid4(),
        locale="hi",
        field_name="title",
        translated_by_user_id=uuid.uuid4(),
        reviewed_by_user_id=None,
        id=uuid.uuid4(),
    )
    # Must not raise
    translation_events.translation_created(BadSession(), row)
