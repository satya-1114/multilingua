"""Integration tests for the Public Information & QR → Notifications / Audit / Search pipelines."""
from __future__ import annotations

import types
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.public import router as public_router
from app.api.v1 import public_access as pa_router
from app.core.exceptions import install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.public_access import PublicResource, PublicView, QRCode
from app.services import public_access_events, search as search_service


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def pa_engine():
    from app.models.organization import Organization
    from app.models.user import User

    PublicResource.__table__.c["metadata"].type = JSON()
    QRCode.__table__.c["metadata"].type = JSON()
    AuditLog.__table__.c["metadata"].type = JSON()

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    from app.database.base import Base
    import app.models  # noqa: F401  (register all mappers)

    # Swap PG-only column types for SQLite-compatible variants.
    for tbl in Base.metadata.tables.values():
        for col in tbl.columns:
            cls_name = col.type.__class__.__name__
            if cls_name == "JSONB":
                col.type = JSON()
            elif cls_name == "ARRAY":
                col.type = JSON()
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def Session(pa_engine):
    return sessionmaker(bind=pa_engine, autoflush=False, autocommit=False, future=True)


def _fake_user(role: str, user_id: uuid.UUID | None = None):
    return types.SimpleNamespace(
        id=user_id or uuid.uuid4(),
        roles=[types.SimpleNamespace(name=role)],
        is_active=True,
        deleted_at=None,
    )


def _build_client(Session, user=None):
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(
        pa_router.router, prefix="/public-resources", tags=["public-access"]
    )
    app.include_router(public_router, prefix="/public", tags=["public"])

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


def _new_slug(prefix: str = "s") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


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


def _mk_resource(client, **overrides) -> str:
    payload = {
        "resourceType": "campaign",
        "slug": _new_slug(),
        "title": "T",
        "visibility": "public",
    }
    payload.update(overrides)
    r = client.post("/public-resources", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


# --------------------------------------------------------------------------- #
# PublicResource lifecycle → notifications + audit
# --------------------------------------------------------------------------- #


def test_resource_lifecycle_emits_notifications_and_audit(Session):
    mgr = _fake_user("campaign_manager")
    client = _build_client(Session, mgr)

    rid = _mk_resource(client, title="Awareness")

    # Owner gets a "created" notification.
    titles = [n.title.lower() for n in _notifs(Session, mgr.id)]
    assert any("created" in t for t in titles)

    client.patch(f"/public-resources/{rid}", json={"description": "d"})
    client.post(f"/public-resources/{rid}/unpublish")
    client.post(f"/public-resources/{rid}/publish")
    client.post(
        f"/public-resources/{rid}/regenerate-slug",
        json={"slug": _new_slug("new")},
    )
    client.post(f"/public-resources/{rid}/regenerate-qr-token")
    client.post(f"/public-resources/{rid}/expire")

    titles = [n.title.lower() for n in _notifs(Session, mgr.id)]
    for keyword in (
        "created", "updated", "unpublished", "published",
        "slug regenerated", "qr token regenerated", "expired",
    ):
        assert any(keyword in t for t in titles), f"missing notif: {keyword}"

    actions = [a.action for a in _audits(Session, "public_resource")]
    for act in (
        "create", "update", "unpublish", "publish",
        "regenerate_slug", "regenerate_qr_token", "expire",
    ):
        assert act in actions, f"missing audit action {act}: {actions}"


# --------------------------------------------------------------------------- #
# QRCode lifecycle → notifications + audit
# --------------------------------------------------------------------------- #


def test_qr_lifecycle_emits_notifications_and_audit(Session):
    mgr = _fake_user("campaign_manager")
    client = _build_client(Session, mgr)
    rid = _mk_resource(client, title="Q")

    c = client.post(f"/public-resources/{rid}/qr", json={"format": "png"})
    qid = c.json()["data"]["id"]
    client.patch(f"/public-resources/qr/{qid}/activate")
    client.patch(f"/public-resources/qr/{qid}/deactivate")
    c2 = client.post(f"/public-resources/{rid}/qr", json={"format": "svg"})
    qid2 = c2.json()["data"]["id"]
    client.patch(f"/public-resources/qr/{qid2}/regenerate", json={"format": "pdf"})

    titles = [n.title.lower() for n in _notifs(Session, mgr.id)]
    for keyword in ("qr code registered", "qr code activated",
                    "qr code deactivated", "qr code regenerated"):
        assert any(keyword in t for t in titles), f"missing notif: {keyword}"

    actions = [a.action for a in _audits(Session, "qr_code")]
    for act in ("create", "activate", "deactivate", "regenerate"):
        assert act in actions, f"missing qr audit action {act}: {actions}"


# --------------------------------------------------------------------------- #
# Anonymous view registration → aggregate-safe audit only
# --------------------------------------------------------------------------- #


def test_anonymous_view_writes_aggregate_safe_audit(Session):
    mgr = _build_client(Session, _fake_user("campaign_manager"))
    slug = _new_slug("aud")
    rid = _mk_resource(mgr, slug=slug)

    anon = _build_client(Session)
    anon.post(
        f"/public/p/{slug}/view",
        json={"deviceType": "mobile", "country": "IN"},
        headers={"user-agent": "pytest/1.0"},
    )

    rows = _audits(Session, "public_view")
    assert len(rows) == 1
    row = rows[0]
    assert row.action == "view"
    assert row.actor_id is None
    assert row.entity_id == rid
    # No PII: only country / device aggregation.
    meta = row.metadata_ or {}
    assert set(meta.keys()) <= {"country", "deviceType"}
    assert meta.get("country") == "IN"
    # IP / UA / referrer must not be persisted in audit metadata.
    assert "ip" not in meta and "userAgent" not in meta and "referrer" not in meta


# --------------------------------------------------------------------------- #
# Event helper isolation
# --------------------------------------------------------------------------- #


def test_public_access_events_swallow_notification_failures(Session, monkeypatch):
    """A notification failure must never bubble out of an event emitter."""
    from app.services import notifications as notif

    def _boom(*a, **kw):
        raise RuntimeError("notify down")

    monkeypatch.setattr(notif, "create", _boom)

    s = Session()
    try:
        r = PublicResource(
            resource_type="campaign",
            slug=_new_slug("iso"),
            title="Silent",
            visibility="public",
            created_by_user_id=uuid.uuid4(),
            metadata_={},
        )
        s.add(r)
        s.commit()
        # Should NOT raise.
        public_access_events.resource_created(s, r)
        public_access_events.resource_published(s, r)
        public_access_events.slug_regenerated(s, r)
    finally:
        s.close()


def test_notification_failure_does_not_abort_business_op(Session, monkeypatch):
    """A failing notifier must not prevent the resource from being created."""
    from app.services import notifications as notif

    monkeypatch.setattr(notif, "create", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("down")))

    mgr = _fake_user("campaign_manager")
    client = _build_client(Session, mgr)
    slug = _new_slug("nof")
    r = client.post(
        "/public-resources",
        json={"resourceType": "campaign", "slug": slug, "title": "OK"},
    )
    assert r.status_code == 201, r.text
    # Audit still recorded.
    actions = [a.action for a in _audits(Session, "public_resource")]
    assert "create" in actions


# --------------------------------------------------------------------------- #
# Search-scope registration
# --------------------------------------------------------------------------- #


def test_search_scope_registered():
    assert "public_resource" in search_service.SCOPE_PERMISSIONS
    assert search_service.SCOPE_PERMISSIONS["public_resource"] == "public:view"
    assert "public_resource" in search_service._HANDLERS


def test_search_public_resource_finds_by_title(Session):
    mgr = _fake_user("campaign_manager")
    client = _build_client(Session, mgr)
    _mk_resource(client, title="UniqueAwarenessBanner", slug=_new_slug("uab"))

    s = Session()
    try:
        res = search_service.search(
            s,
            q="UniqueAwarenessBanner",
            permissions={"public:view"},
            scopes=["public_resource"],
        )
        titles = [h["title"] for h in res["results"]]
        assert "UniqueAwarenessBanner" in titles
    finally:
        s.close()
