"""Unit tests for public_access repository & service layer.

Runs against SQLite in-memory. Postgres-specific JSONB is swapped for
plain JSON — a test-only shim; nothing under ``app/`` changes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.public_access import (
    QR_STATUS_ACTIVE,
    QR_STATUS_EXPIRED,
    QR_STATUS_PENDING,
    QR_STATUS_REVOKED,
    RESOURCE_TYPE_DISASTER,
    VISIBILITY_PRIVATE,
    VISIBILITY_PUBLIC,
    VISIBILITY_UNLISTED,
)
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.models.public_access import PublicResource, PublicView, QRCode
from app.repositories.public_access import (
    public_resources,
    qr_codes,
)
from app.services import public_access as svc


MANAGER_ROLES = ("org_admin",)  # public:* + qr:*
CREATOR_ROLES = ("content_creator",)  # public:create/update, qr:create/view
VIEWER_ROLES = ("viewer",)  # public:view + qr:view only
VOLUNTEER_ROLES = ("volunteer",)  # public:view only


# --------------------------------------------------------------------------- #
# Test-only DB: swap Postgres JSONB for SQLite JSON.
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def sqlite_engine():
    from app.models.organization import Organization
    from app.models.user import User

    PublicResource.__table__.c["metadata"].type = JSON()
    QRCode.__table__.c["metadata"].type = JSON()

    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
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
def db(sqlite_engine):
    Session = sessionmaker(
        bind=sqlite_engine, autoflush=False, autocommit=False, future=True
    )
    s = Session()
    try:
        yield s
    finally:
        s.rollback()
        for tbl in (
            PublicView.__table__,
            QRCode.__table__,
            PublicResource.__table__,
        ):
            s.execute(tbl.delete())
        s.commit()
        s.close()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make(db, **overrides) -> PublicResource:
    payload = {
        "resourceType": overrides.pop("resourceType", RESOURCE_TYPE_DISASTER),
        "slug": overrides.pop("slug", f"slug-{uuid.uuid4().hex[:8]}"),
        "title": overrides.pop("title", "Flood alert"),
        **overrides,
    }
    return svc.create_public_resource(
        db, roles=MANAGER_ROLES, created_by=None, payload=payload
    )


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


class TestRepository:
    def test_search_pagination(self, db):
        for i in range(3):
            _make(db, title=f"T{i}", slug=f"t-{i}")
        items, total = public_resources.search(db, page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

    def test_get_by_slug_and_qr_token(self, db):
        r = _make(db, slug="my-page")
        assert public_resources.get_by_slug(db, "my-page").id == r.id
        assert public_resources.get_by_slug(db, "missing") is None

        svc.regenerate_qr_token(db, roles=MANAGER_ROLES, resource_id=r.id)
        db.refresh(r)
        assert public_resources.get_by_qr_token(db, r.qr_token).id == r.id

    def test_list_public_filters_by_visibility(self, db):
        r_pub = _make(db, slug="pub")
        r_priv = _make(db, slug="priv")
        svc.unpublish_public_resource(
            db, roles=MANAGER_ROLES, resource_id=r_priv.id
        )
        result = public_resources.list_public(db)
        ids = {x.id for x in result}
        assert r_pub.id in ids
        assert r_priv.id not in ids

    def test_list_by_resource(self, db):
        rid = uuid.uuid4()
        _make(db, slug="a", resourceId=rid)
        _make(db, slug="b", resourceId=rid)
        _make(db, slug="c")  # different resource_id
        items = public_resources.list_by_resource(
            db, resource_type=RESOURCE_TYPE_DISASTER, resource_id=rid
        )
        assert len(items) == 2

    def test_search_active_only(self, db):
        _make(db, slug="live")
        expired = _make(db, slug="soon", expiresAt=datetime.now(timezone.utc) + timedelta(hours=1))
        svc.expire_public_resource(db, roles=MANAGER_ROLES, resource_id=expired.id)
        items, total = public_resources.search(db, active_only=True)
        assert total == 1
        assert items[0].slug == "live"


# --------------------------------------------------------------------------- #
# PublicResource service
# --------------------------------------------------------------------------- #


class TestPublicResourceService:
    def test_create_defaults_and_validates(self, db):
        r = _make(db)
        assert r.visibility == VISIBILITY_PUBLIC
        assert r.qr_token is None

    def test_create_requires_permission(self, db):
        with pytest.raises(ForbiddenError):
            svc.create_public_resource(
                db,
                roles=VIEWER_ROLES,
                created_by=None,
                payload={
                    "resourceType": RESOURCE_TYPE_DISASTER,
                    "slug": "x",
                    "title": "x",
                },
            )

    def test_create_rejects_bad_slug(self, db):
        with pytest.raises(ValidationError):
            svc.create_public_resource(
                db,
                roles=MANAGER_ROLES,
                created_by=None,
                payload={
                    "resourceType": RESOURCE_TYPE_DISASTER,
                    "slug": "Bad Slug!",
                    "title": "x",
                },
            )

    def test_create_rejects_invalid_resource_type(self, db):
        with pytest.raises(ValidationError):
            svc.create_public_resource(
                db,
                roles=MANAGER_ROLES,
                created_by=None,
                payload={"resourceType": "volcano", "slug": "x", "title": "x"},
            )

    def test_create_rejects_past_expiry(self, db):
        with pytest.raises(ValidationError):
            svc.create_public_resource(
                db,
                roles=MANAGER_ROLES,
                created_by=None,
                payload={
                    "resourceType": RESOURCE_TYPE_DISASTER,
                    "slug": "s",
                    "title": "t",
                    "expiresAt": datetime.now(timezone.utc) - timedelta(days=1),
                },
            )

    def test_duplicate_slug_conflict(self, db):
        _make(db, slug="dup")
        with pytest.raises(ConflictError):
            _make(db, slug="dup")

    def test_update_reslug_and_visibility(self, db):
        r = _make(db, slug="v1")
        updated = svc.update_public_resource(
            db,
            roles=MANAGER_ROLES,
            resource_id=r.id,
            payload={"slug": "v2", "visibility": VISIBILITY_UNLISTED},
        )
        assert updated.slug == "v2"
        assert updated.visibility == VISIBILITY_UNLISTED

    def test_update_conflicts_on_duplicate_slug(self, db):
        _make(db, slug="taken")
        r = _make(db, slug="mine")
        with pytest.raises(ConflictError):
            svc.update_public_resource(
                db, roles=MANAGER_ROLES, resource_id=r.id, payload={"slug": "taken"}
            )

    def test_update_ignores_qr_token_and_resource_type_changes(self, db):
        r = _make(db, slug="s", resourceType=RESOURCE_TYPE_DISASTER)
        updated = svc.update_public_resource(
            db,
            roles=MANAGER_ROLES,
            resource_id=r.id,
            payload={"qrToken": "abc", "resourceType": "campaign"},
        )
        assert updated.qr_token is None
        assert updated.resource_type == RESOURCE_TYPE_DISASTER

    def test_publish_unpublish_lifecycle(self, db):
        r = _make(db)
        svc.unpublish_public_resource(db, roles=MANAGER_ROLES, resource_id=r.id)
        db.refresh(r)
        assert r.visibility == VISIBILITY_PRIVATE

        svc.publish_public_resource(db, roles=MANAGER_ROLES, resource_id=r.id)
        db.refresh(r)
        assert r.visibility == VISIBILITY_PUBLIC

    def test_publish_fails_when_expired(self, db):
        r = _make(db)
        svc.expire_public_resource(db, roles=MANAGER_ROLES, resource_id=r.id)
        with pytest.raises(ConflictError):
            svc.publish_public_resource(db, roles=MANAGER_ROLES, resource_id=r.id)

    def test_expire_deactivates_active_qr(self, db):
        r = _make(db)
        qr = svc.create_qr_metadata(
            db, roles=MANAGER_ROLES, resource_id=r.id, payload={"format": "png"}
        )
        svc.activate_qr(db, roles=MANAGER_ROLES, qr_id=qr.id)
        svc.expire_public_resource(db, roles=MANAGER_ROLES, resource_id=r.id)
        db.refresh(qr)
        assert qr.status == QR_STATUS_EXPIRED

    def test_regenerate_qr_token_mints_and_revokes(self, db):
        r = _make(db)
        qr = svc.create_qr_metadata(
            db, roles=MANAGER_ROLES, resource_id=r.id, payload={}
        )
        svc.activate_qr(db, roles=MANAGER_ROLES, qr_id=qr.id)
        old_token = r.qr_token
        svc.regenerate_qr_token(db, roles=MANAGER_ROLES, resource_id=r.id)
        db.refresh(r)
        db.refresh(qr)
        assert r.qr_token != old_token
        assert qr.status == QR_STATUS_REVOKED

    def test_regenerate_slug_permission_and_uniqueness(self, db):
        r = _make(db, slug="orig")
        with pytest.raises(ForbiddenError):
            svc.regenerate_slug(
                db, roles=VOLUNTEER_ROLES, resource_id=r.id, slug="other"
            )
        svc.regenerate_slug(
            db, roles=MANAGER_ROLES, resource_id=r.id, slug="renamed"
        )
        db.refresh(r)
        assert r.slug == "renamed"


# --------------------------------------------------------------------------- #
# Public retrieval (anonymous)
# --------------------------------------------------------------------------- #


class TestPublicRetrieval:
    def test_resolve_by_slug_public(self, db):
        r = _make(db, slug="alert")
        assert svc.resolve_public_by_slug(db, "alert").id == r.id

    def test_resolve_by_slug_missing(self, db):
        with pytest.raises(NotFoundError):
            svc.resolve_public_by_slug(db, "missing")

    def test_resolve_forbidden_when_private(self, db):
        r = _make(db, slug="priv")
        svc.unpublish_public_resource(db, roles=MANAGER_ROLES, resource_id=r.id)
        with pytest.raises(ForbiddenError):
            svc.resolve_public_by_slug(db, "priv")

    def test_resolve_by_qr_token(self, db):
        r = _make(db, slug="q")
        svc.regenerate_qr_token(db, roles=MANAGER_ROLES, resource_id=r.id)
        db.refresh(r)
        assert svc.resolve_public_by_qr_token(db, r.qr_token).id == r.id


# --------------------------------------------------------------------------- #
# QR service
# --------------------------------------------------------------------------- #


class TestQRService:
    def test_create_mints_qr_token_on_first_use(self, db):
        r = _make(db)
        assert r.qr_token is None
        qr = svc.create_qr_metadata(
            db, roles=MANAGER_ROLES, resource_id=r.id, payload={}
        )
        db.refresh(r)
        assert r.qr_token is not None
        assert qr.status == QR_STATUS_PENDING
        assert qr.format == "png"

    def test_create_rejects_bad_format_and_version(self, db):
        r = _make(db)
        with pytest.raises(ValidationError):
            svc.create_qr_metadata(
                db, roles=MANAGER_ROLES, resource_id=r.id,
                payload={"format": "bmp"},
            )
        with pytest.raises(ValidationError):
            svc.create_qr_metadata(
                db, roles=MANAGER_ROLES, resource_id=r.id,
                payload={"version": 99},
            )

    def test_activate_supersedes_previous(self, db):
        r = _make(db)
        q1 = svc.create_qr_metadata(db, roles=MANAGER_ROLES, resource_id=r.id, payload={})
        q2 = svc.create_qr_metadata(db, roles=MANAGER_ROLES, resource_id=r.id, payload={})
        svc.activate_qr(db, roles=MANAGER_ROLES, qr_id=q1.id)
        svc.activate_qr(db, roles=MANAGER_ROLES, qr_id=q2.id)
        db.refresh(q1)
        db.refresh(q2)
        assert q1.status == QR_STATUS_REVOKED
        assert q2.status == QR_STATUS_ACTIVE
        assert qr_codes.latest_active(db, r.id).id == q2.id

    def test_activate_rejects_revoked(self, db):
        r = _make(db)
        qr = svc.create_qr_metadata(db, roles=MANAGER_ROLES, resource_id=r.id, payload={})
        svc.deactivate_qr(db, roles=MANAGER_ROLES, qr_id=qr.id)
        with pytest.raises(ConflictError):
            svc.activate_qr(db, roles=MANAGER_ROLES, qr_id=qr.id)

    def test_regenerate_metadata_creates_new_and_revokes_old(self, db):
        r = _make(db)
        qr = svc.create_qr_metadata(db, roles=MANAGER_ROLES, resource_id=r.id, payload={})
        svc.activate_qr(db, roles=MANAGER_ROLES, qr_id=qr.id)
        fresh = svc.regenerate_qr_metadata(
            db, roles=MANAGER_ROLES, qr_id=qr.id, payload={"format": "svg"}
        )
        db.refresh(qr)
        assert qr.status == QR_STATUS_REVOKED
        assert fresh.format == "svg"
        assert fresh.status == QR_STATUS_PENDING

    def test_list_qr_codes_permission(self, db):
        r = _make(db)
        svc.create_qr_metadata(db, roles=MANAGER_ROLES, resource_id=r.id, payload={})
        with pytest.raises(ForbiddenError):
            svc.list_qr_codes(db, roles=VOLUNTEER_ROLES, resource_id=r.id)
        assert len(svc.list_qr_codes(db, roles=VIEWER_ROLES, resource_id=r.id)) == 1


# --------------------------------------------------------------------------- #
# View registration
# --------------------------------------------------------------------------- #


class TestViewRegistration:
    def test_register_hashes_ip_and_ua(self, db):
        r = _make(db)
        view = svc.register_view(
            db,
            resource_id=r.id,
            ip="203.0.113.5",
            user_agent="Mozilla/5.0",
            country="IN",
            device_type="mobile",
        )
        assert view is not None
        assert view.ip_hash != "203.0.113.5"
        assert view.user_agent_hash != "Mozilla/5.0"
        assert len(view.ip_hash) == 64
        assert view.country == "IN"

    def test_register_suppresses_rapid_duplicate(self, db):
        r = _make(db)
        first = svc.register_view(
            db, resource_id=r.id, ip="1.2.3.4", user_agent="ua"
        )
        second = svc.register_view(
            db, resource_id=r.id, ip="1.2.3.4", user_agent="ua"
        )
        assert first is not None
        assert second is None

    def test_register_forbidden_when_private(self, db):
        r = _make(db)
        svc.unpublish_public_resource(db, roles=MANAGER_ROLES, resource_id=r.id)
        with pytest.raises(ForbiddenError):
            svc.register_view(db, resource_id=r.id)

    def test_register_rejects_bad_device(self, db):
        r = _make(db)
        with pytest.raises(ValidationError):
            svc.register_view(db, resource_id=r.id, device_type="watch")

    def test_register_rejects_bad_country(self, db):
        r = _make(db)
        with pytest.raises(ValidationError):
            svc.register_view(db, resource_id=r.id, country="India")

    def test_register_truncates_long_referrer(self, db):
        r = _make(db)
        view = svc.register_view(
            db, resource_id=r.id, ip="9.9.9.9", referrer="x" * 5000
        )
        assert view is not None
        assert len(view.referrer) == 1024

    def test_summarize_views_shape(self, db):
        r = _make(db)
        svc.register_view(db, resource_id=r.id, ip="a", country="IN", device_type="mobile")
        svc.register_view(db, resource_id=r.id, ip="b", country="US", device_type="desktop")
        summary = svc.summarize_views(db, roles=VIEWER_ROLES, resource_id=r.id)
        assert summary["total"] == 2
        assert summary["byCountry"]["IN"] == 1
        assert summary["byDevice"]["mobile"] == 1


# --------------------------------------------------------------------------- #
# Search filters
# --------------------------------------------------------------------------- #


class TestSearchFilters:
    def test_filter_by_resource_type_and_visibility(self, db):
        _make(db, slug="a", resourceType=RESOURCE_TYPE_DISASTER)
        r2 = _make(db, slug="b", resourceType="campaign")
        svc.unpublish_public_resource(db, roles=MANAGER_ROLES, resource_id=r2.id)
        items, total = public_resources.search(
            db, resource_type="campaign", visibility=VISIBILITY_PRIVATE
        )
        assert total == 1
        assert items[0].id == r2.id

    def test_search_text_matches_title_slug(self, db):
        _make(db, slug="chennai-flood", title="Chennai Flood")
        _make(db, slug="delhi-fire", title="Delhi Fire")
        items, total = public_resources.search(db, search="chennai")
        assert total == 1
        assert items[0].slug == "chennai-flood"
