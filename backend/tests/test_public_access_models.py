"""Schema, enum, model, and RBAC tests for the Public Information & QR module.

DB-foundation only — no repository/service/router yet.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.constants.public_access import (
    QR_FORMATS,
    QR_FORMAT_PNG,
    QR_STATUSES,
    QR_STATUS_ACTIVE,
    QR_STATUS_PENDING,
    RESOURCE_TYPES,
    RESOURCE_TYPE_DISASTER,
    VISIBILITIES,
    VISIBILITIES_RETRIEVABLE,
    VISIBILITY_DISABLED,
    VISIBILITY_PRIVATE,
    VISIBILITY_PUBLIC,
    VISIBILITY_UNLISTED,
)
from app.models.public_access import PublicResource, PublicView, QRCode
from app.schemas.public_access import (
    PublicResourceCreate,
    PublicResourceDto,
    PublicResourceUpdate,
    PublicViewCreate,
    PublicViewDto,
    QRCodeCreate,
    QRCodeDto,
    QRCodeUpdate,
)
from app.security.rbac import has_permission


# -- Enums --------------------------------------------------------------------


def test_enum_membership_matches_schema_literals():
    assert RESOURCE_TYPE_DISASTER in RESOURCE_TYPES
    assert VISIBILITY_PUBLIC in VISIBILITIES
    assert QR_STATUS_ACTIVE in QR_STATUSES
    assert QR_FORMAT_PNG in QR_FORMATS


def test_retrievable_visibilities_are_subset():
    assert set(VISIBILITIES_RETRIEVABLE).issubset(set(VISIBILITIES))
    assert VISIBILITY_PUBLIC in VISIBILITIES_RETRIEVABLE
    assert VISIBILITY_UNLISTED in VISIBILITIES_RETRIEVABLE
    assert VISIBILITY_PRIVATE not in VISIBILITIES_RETRIEVABLE
    assert VISIBILITY_DISABLED not in VISIBILITIES_RETRIEVABLE


# -- Schemas ------------------------------------------------------------------


def test_public_resource_create_defaults():
    payload = PublicResourceCreate(
        resourceType="disaster",
        slug="chennai-floods-2026",
        title="Chennai Floods 2026",
    )
    assert payload.visibility == "public"
    assert payload.metadata == {}
    assert payload.resourceId is None


def test_public_resource_create_rejects_bad_slug():
    with pytest.raises(Exception):
        PublicResourceCreate(
            resourceType="disaster", slug="Bad Slug!", title="x"
        )
    with pytest.raises(Exception):
        PublicResourceCreate(
            resourceType="disaster", slug="-leading", title="x"
        )


def test_public_resource_create_rejects_invalid_type():
    with pytest.raises(Exception):
        PublicResourceCreate(
            resourceType="volcano",  # type: ignore[arg-type]
            slug="ok",
            title="x",
        )


def test_public_resource_update_all_optional():
    upd = PublicResourceUpdate()
    assert upd.model_dump(exclude_none=True) == {}


def test_public_resource_dto_maps_snake_case():
    now = datetime.now(timezone.utc)
    dto = PublicResourceDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "resource_type": "disaster",
            "resource_id": uuid.uuid4(),
            "slug": "flood-alert",
            "qr_token": "abc123",
            "title": "Flood alert",
            "visibility": "public",
            "expires_at": now + timedelta(days=30),
            "metadata_": {"theme": "dark"},
        }
    )
    assert dto.resourceType == "disaster"
    assert dto.slug == "flood-alert"
    assert dto.qrToken == "abc123"
    assert dto.metadata == {"theme": "dark"}


def test_qr_code_create_defaults():
    q = QRCodeCreate()
    assert q.format == "png"
    assert q.version == 1
    assert q.metadata == {}


def test_qr_code_create_rejects_bad_version():
    with pytest.raises(Exception):
        QRCodeCreate(version=41)
    with pytest.raises(Exception):
        QRCodeCreate(version=0)


def test_qr_code_update_all_optional():
    assert QRCodeUpdate().model_dump(exclude_none=True) == {}


def test_qr_code_dto_maps_snake_case():
    now = datetime.now(timezone.utc)
    dto = QRCodeDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "public_resource_id": uuid.uuid4(),
            "format": "png",
            "version": 3,
            "status": QR_STATUS_PENDING,
            "generated_at": now,
            "metadata_": {},
        }
    )
    assert dto.format == "png"
    assert dto.version == 3
    assert dto.status == "pending"


def test_public_view_create_country_length():
    with pytest.raises(Exception):
        PublicViewCreate(country="INDIA")  # too long


def test_public_view_dto_maps_snake_case():
    now = datetime.now(timezone.utc)
    dto = PublicViewDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "public_resource_id": uuid.uuid4(),
            "viewed_at": now,
            "ip_hash": "h1",
            "user_agent_hash": "h2",
            "country": "IN",
            "device_type": "mobile",
            "referrer": "https://x.example",
        }
    )
    assert dto.country == "IN"
    assert dto.deviceType == "mobile"


# -- Model / metadata --------------------------------------------------------


def test_models_are_registered_on_metadata():
    from app.database.base import Base

    tables = set(Base.metadata.tables)
    assert "public_resources" in tables
    assert "qr_codes" in tables
    assert "public_views" in tables


def test_model_indexes_and_constraints():
    constraints = {c.name for c in PublicResource.__table__.constraints}
    assert "uq_public_resources_slug" in constraints
    assert "uq_public_resources_qr_token" in constraints

    pr_idx = {i.name for i in PublicResource.__table__.indexes}
    assert "ix_public_resources_resource" in pr_idx
    assert "ix_public_resources_org_visibility" in pr_idx
    assert "ix_public_resources_visibility_expires" in pr_idx

    qr_idx = {i.name for i in QRCode.__table__.indexes}
    assert "ix_qr_codes_resource_status" in qr_idx

    pv_idx = {i.name for i in PublicView.__table__.indexes}
    assert "ix_public_views_resource_viewed" in pv_idx


def test_qr_cascades_on_public_resource_delete():
    fks = list(QRCode.__table__.foreign_keys)
    assert any(fk.ondelete == "CASCADE" for fk in fks)
    view_fks = list(PublicView.__table__.foreign_keys)
    assert any(fk.ondelete == "CASCADE" for fk in view_fks)


# -- RBAC ---------------------------------------------------------------------


def test_rbac_grants_new_public_permissions():
    # super_admin has wildcard
    assert has_permission(["super_admin"], "public:manage")
    assert has_permission(["super_admin"], "qr:manage")

    # org_admin gets public:* and qr:*
    assert has_permission(["org_admin"], "public:create")
    assert has_permission(["org_admin"], "public:manage")
    assert has_permission(["org_admin"], "qr:create")
    assert has_permission(["org_admin"], "qr:manage")

    # campaign_manager can manage public resources & QR
    assert has_permission(["campaign_manager"], "public:view")
    assert has_permission(["campaign_manager"], "public:create")
    assert has_permission(["campaign_manager"], "qr:create")

    # communication_officer can view/manage public + qr for reach
    assert has_permission(["communication_officer"], "public:view")
    assert has_permission(["communication_officer"], "qr:view")

    # viewer / data_analyst can view but not mutate
    assert has_permission(["viewer"], "public:view")
    assert not has_permission(["viewer"], "public:update")
    assert has_permission(["data_analyst"], "public:view")
    assert not has_permission(["data_analyst"], "qr:manage")

    # volunteer role: no public/qr management
    assert not has_permission(["volunteer"], "public:create")
    assert not has_permission(["volunteer"], "qr:manage")
