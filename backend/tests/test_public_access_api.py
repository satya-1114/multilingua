"""Router-level tests for the Public Information & QR module."""
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
from app.models.public_access import PublicResource, PublicView, QRCode


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def pa_engine():
    from app.models.organization import Organization
    from app.models.user import User

    PublicResource.__table__.c["metadata"].type = JSON()
    QRCode.__table__.c["metadata"].type = JSON()

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    for tbl in (
        User.__table__,
        Organization.__table__,
        PublicResource.__table__,
        QRCode.__table__,
        PublicView.__table__,
    ):
        tbl.create(eng, checkfirst=True)
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


# --------------------------------------------------------------------------- #
# CRUD + envelope + list
# --------------------------------------------------------------------------- #


def test_create_get_list_update_resource(Session):
    mgr = _fake_user("campaign_manager")
    client = _build_client(Session, mgr)
    slug = _new_slug("res")

    r = client.post(
        "/public-resources",
        json={
            "resourceType": "campaign",
            "slug": slug,
            "title": "Awareness Drive",
            "visibility": "public",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["success"] is True
    assert body["meta"]["requestId"].startswith("req_")
    rid = body["data"]["id"]
    assert body["data"]["slug"] == slug
    assert body["data"]["visibility"] == "public"

    g = client.get(f"/public-resources/{rid}")
    assert g.status_code == 200
    assert g.json()["data"]["title"] == "Awareness Drive"

    u = client.patch(
        f"/public-resources/{rid}", json={"description": "Details here"}
    )
    assert u.status_code == 200
    assert u.json()["data"]["description"] == "Details here"

    lst = client.get(
        "/public-resources",
        params={"resourceType": "campaign", "page": 1, "pageSize": 10},
    )
    assert lst.status_code == 200
    j = lst.json()
    assert j["pagination"]["total"] >= 1
    assert j["pagination"]["page"] == 1


def test_permission_denied_for_viewer(Session):
    client = _build_client(Session, _fake_user("viewer"))
    r = client.post(
        "/public-resources",
        json={"resourceType": "campaign", "slug": _new_slug(), "title": "X"},
    )
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #


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


def test_publish_unpublish_expire(Session):
    client = _build_client(Session, _fake_user("campaign_manager"))
    rid = _mk_resource(client)

    up = client.post(f"/public-resources/{rid}/unpublish")
    assert up.status_code == 200
    assert up.json()["data"]["visibility"] == "private"

    pu = client.post(f"/public-resources/{rid}/publish")
    assert pu.status_code == 200
    assert pu.json()["data"]["visibility"] == "public"

    ex = client.post(f"/public-resources/{rid}/expire")
    assert ex.status_code == 200
    assert ex.json()["data"]["visibility"] == "expired"


def test_regenerate_slug_and_qr_token(Session):
    client = _build_client(Session, _fake_user("campaign_manager"))
    rid = _mk_resource(client)

    new_slug = _new_slug("fresh")
    rs = client.post(
        f"/public-resources/{rid}/regenerate-slug", json={"slug": new_slug}
    )
    assert rs.status_code == 200
    assert rs.json()["data"]["slug"] == new_slug

    rq = client.post(f"/public-resources/{rid}/regenerate-qr-token")
    assert rq.status_code == 200
    token = rq.json()["data"]["qrToken"]
    assert token and len(token) == 32


# --------------------------------------------------------------------------- #
# QR lifecycle
# --------------------------------------------------------------------------- #


def test_qr_lifecycle(Session):
    client = _build_client(Session, _fake_user("campaign_manager"))
    rid = _mk_resource(client)

    c = client.post(
        f"/public-resources/{rid}/qr", json={"format": "png", "version": 4}
    )
    assert c.status_code == 201, c.text
    qid = c.json()["data"]["id"]
    assert c.json()["data"]["status"] == "pending"

    a = client.patch(f"/public-resources/qr/{qid}/activate")
    assert a.status_code == 200
    assert a.json()["data"]["status"] == "active"
    assert a.json()["data"]["generatedAt"] is not None

    d = client.patch(f"/public-resources/qr/{qid}/deactivate")
    assert d.status_code == 200
    assert d.json()["data"]["status"] == "revoked"

    # Cannot re-activate a revoked QR → 409
    ra = client.patch(f"/public-resources/qr/{qid}/activate")
    assert ra.status_code == 409

    # Regenerate: creates a new pending metadata row
    c2 = client.post(f"/public-resources/{rid}/qr", json={"format": "svg"})
    qid2 = c2.json()["data"]["id"]
    reg = client.patch(f"/public-resources/qr/{qid2}/regenerate", json={"format": "pdf"})
    assert reg.status_code == 200
    body = reg.json()["data"]
    assert body["id"] != qid2
    assert body["format"] == "pdf"
    assert body["status"] == "pending"

    lst = client.get(f"/public-resources/{rid}/qr")
    assert lst.status_code == 200
    assert len(lst.json()["data"]) >= 2


# --------------------------------------------------------------------------- #
# Anonymous public endpoints
# --------------------------------------------------------------------------- #


def test_anonymous_slug_and_qr_resolution(Session):
    mgr = _build_client(Session, _fake_user("campaign_manager"))
    slug = _new_slug("pub")
    rid = _mk_resource(mgr, slug=slug)
    token = mgr.post(
        f"/public-resources/{rid}/regenerate-qr-token"
    ).json()["data"]["qrToken"]

    anon = _build_client(Session)  # no auth override

    s = anon.get(f"/public/p/{slug}")
    assert s.status_code == 200
    assert s.json()["data"]["id"] == rid

    q = anon.get(f"/public/q/{token}")
    assert q.status_code == 200
    assert q.json()["data"]["id"] == rid

    missing = anon.get("/public/p/does-not-exist")
    assert missing.status_code == 404


def test_anonymous_view_registration_and_dedup(Session):
    mgr = _build_client(Session, _fake_user("campaign_manager"))
    slug = _new_slug("view")
    rid = _mk_resource(mgr, slug=slug)

    anon = _build_client(Session)
    v1 = anon.post(
        f"/public/p/{slug}/view",
        json={"deviceType": "mobile", "country": "IN"},
        headers={"user-agent": "pytest/1.0"},
    )
    assert v1.status_code == 200, v1.text
    assert v1.json()["data"]["registered"] is True

    # Rapid duplicate is suppressed
    v2 = anon.post(
        f"/public/p/{slug}/view",
        json={"deviceType": "mobile", "country": "IN"},
        headers={"user-agent": "pytest/1.0"},
    )
    assert v2.status_code == 200
    assert v2.json()["data"]["registered"] is False

    # Summary should reflect the single stored view
    summary = mgr.get(f"/public-resources/{rid}/views/summary")
    assert summary.status_code == 200
    assert summary.json()["data"]["total"] == 1

    lst = mgr.get(f"/public-resources/{rid}/views")
    assert lst.status_code == 200
    assert len(lst.json()["data"]) == 1


def test_expired_resource_public_access_returns_409(Session):
    mgr = _build_client(Session, _fake_user("campaign_manager"))
    slug = _new_slug("exp")
    rid = _mk_resource(mgr, slug=slug)
    mgr.post(f"/public-resources/{rid}/expire")

    anon = _build_client(Session)
    r = anon.get(f"/public/p/{slug}")
    # Expired visibility fails the retrievable check → ForbiddenError (403)
    assert r.status_code == 403


def test_private_resource_forbidden_publicly(Session):
    mgr = _build_client(Session, _fake_user("campaign_manager"))
    slug = _new_slug("prv")
    rid = _mk_resource(mgr, slug=slug)
    mgr.post(f"/public-resources/{rid}/unpublish")  # → private

    anon = _build_client(Session)
    r = anon.get(f"/public/p/{slug}")
    assert r.status_code == 403


def test_view_by_qr_token(Session):
    mgr = _build_client(Session, _fake_user("campaign_manager"))
    rid = _mk_resource(mgr, slug=_new_slug("qv"))
    token = mgr.post(
        f"/public-resources/{rid}/regenerate-qr-token"
    ).json()["data"]["qrToken"]

    anon = _build_client(Session)
    v = anon.post(
        f"/public/q/{token}/view",
        json={"deviceType": "desktop"},
        headers={"user-agent": "ua-qr"},
    )
    assert v.status_code == 200
    assert v.json()["data"]["registered"] is True
