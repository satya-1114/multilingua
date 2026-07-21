"""Model, schema, enum, and RBAC tests for the multilingual platform.

Phase 5.1 — DB foundation only. No repository/service/router exists yet.
SQLite in-memory; JSONB columns are swapped for JSON so the tables build.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import JSON, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.constants.translation import (
    ENTITY_TYPE_DISASTER,
    ENTITY_TYPE_PUBLIC_RESOURCE,
    JOB_STATUSES,
    JOB_STATUS_PENDING,
    PROVIDERS,
    PROVIDER_MANUAL,
    SUPPORTED_ENTITY_TYPES,
    TRANSLATION_STATUSES,
    TRANSLATION_STATUS_DRAFT,
    TRANSLATION_STATUS_PUBLISHED,
)
from app.models.translation import Translation, TranslationJob, TranslationLocale
from app.schemas.translation import (
    EntityTranslationCreate,
    EntityTranslationDto,
    EntityTranslationUpdate,
    TranslationJobCreate,
    TranslationJobDto,
    TranslationLocaleCreate,
    TranslationLocaleDto,
    TranslationLocaleUpdate,
)
from app.security.rbac import has_permission


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


def test_enum_membership():
    assert TRANSLATION_STATUS_DRAFT in TRANSLATION_STATUSES
    assert TRANSLATION_STATUS_PUBLISHED in TRANSLATION_STATUSES
    assert JOB_STATUS_PENDING in JOB_STATUSES
    assert PROVIDER_MANUAL in PROVIDERS
    for et in (ENTITY_TYPE_DISASTER, ENTITY_TYPE_PUBLIC_RESOURCE):
        assert et in SUPPORTED_ENTITY_TYPES


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


def test_entity_translation_create_defaults():
    dto = EntityTranslationCreate(
        entity_type="disaster",
        entity_id=uuid.uuid4(),
        locale="hi",
        field_name="title",
    )
    assert dto.status == "draft"
    assert dto.translatedValue == ""
    assert dto.metadata == {}


def test_entity_translation_create_rejects_bad_entity():
    with pytest.raises(ValidationError):
        EntityTranslationCreate(
            entity_type="unknown", entity_id=uuid.uuid4(), locale="en", field_name="x"
        )


def test_entity_translation_create_rejects_bad_status():
    with pytest.raises(ValidationError):
        EntityTranslationCreate(
            entity_type="campaign",
            entity_id=uuid.uuid4(),
            locale="en",
            field_name="title",
            status="approved",  # not a valid status
        )


def test_entity_translation_update_partial():
    upd = EntityTranslationUpdate(translated_value="नमस्ते", status="translated")
    assert upd.translatedValue == "नमस्ते"
    assert upd.status == "translated"
    assert upd.metadata is None


def test_locale_create_rejects_short_locale():
    with pytest.raises(ValidationError):
        TranslationLocaleCreate(locale="e", display_name="English")


def test_locale_update_partial():
    upd = TranslationLocaleUpdate(enabled=False, sort_order=10)
    assert upd.enabled is False
    assert upd.sortOrder == 10


def test_job_create_ok():
    job = TranslationJobCreate(
        entity_type="organization",
        entity_id=uuid.uuid4(),
        source_locale="en",
        target_locale="hi",
        provider="ai",
    )
    assert job.targetLocale == "hi"


# --------------------------------------------------------------------------- #
# Model / DB constraints (SQLite w/ JSON swap)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def engine():
    from app.models.user import User  # register user table for FKs

    Translation.__table__.c["metadata"].type = JSON()
    TranslationJob.__table__.c["metadata"].type = JSON()

    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
    )
    for tbl in (
        User.__table__,
        Translation.__table__,
        TranslationJob.__table__,
        TranslationLocale.__table__,
    ):
        tbl.create(eng, checkfirst=True)
    return eng


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.rollback()
        for tbl in (
            Translation.__table__,
            TranslationJob.__table__,
            TranslationLocale.__table__,
        ):
            s.execute(tbl.delete())
        s.commit()
        s.close()


def test_translation_unique_scope(db):
    eid = uuid.uuid4()
    db.add(
        Translation(
            entity_type="disaster",
            entity_id=eid,
            locale="hi",
            field_name="title",
            translated_value="A",
        )
    )
    db.commit()

    db.add(
        Translation(
            entity_type="disaster",
            entity_id=eid,
            locale="hi",
            field_name="title",
            translated_value="B",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Different field_name is fine.
    db.add(
        Translation(
            entity_type="disaster",
            entity_id=eid,
            locale="hi",
            field_name="description",
            translated_value="B",
        )
    )
    db.commit()


def test_locale_unique(db):
    db.add(TranslationLocale(locale="en", display_name="English", default_locale=True))
    db.commit()
    db.add(TranslationLocale(locale="en", display_name="English (dup)"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_job_persists_defaults(db):
    job = TranslationJob(
        entity_type="campaign",
        entity_id=uuid.uuid4(),
        source_locale="en",
        target_locale="hi",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    assert job.status == "pending"
    assert job.metadata_ == {}


def test_dto_serialization_from_orm(db):
    eid = uuid.uuid4()
    row = Translation(
        entity_type="public_resource",
        entity_id=eid,
        locale="ta",
        field_name="title",
        translated_value="தலைப்பு",
        status="translated",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    dto = EntityTranslationDto.model_validate(
        {
            "id": row.id,
            "createdAt": row.created_at,
            "updatedAt": row.updated_at,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "locale": row.locale,
            "field_name": row.field_name,
            "translated_value": row.translated_value,
            "status": row.status,
            "source_hash": row.source_hash,
            "translated_by_user_id": row.translated_by_user_id,
            "reviewed_by_user_id": row.reviewed_by_user_id,
            "metadata": row.metadata_,
        }
    )
    assert dto.locale == "ta"
    assert dto.translatedValue == "தலைப்பு"
    assert dto.status == "translated"

    locale_row = TranslationLocale(
        locale="ta", display_name="Tamil", native_name="தமிழ்", sort_order=5
    )
    db.add(locale_row)
    db.commit()
    db.refresh(locale_row)
    ldto = TranslationLocaleDto.model_validate(
        {
            "id": locale_row.id,
            "createdAt": locale_row.created_at,
            "updatedAt": locale_row.updated_at,
            "locale": locale_row.locale,
            "display_name": locale_row.display_name,
            "native_name": locale_row.native_name,
            "rtl": locale_row.rtl,
            "enabled": locale_row.enabled,
            "default_locale": locale_row.default_locale,
            "sort_order": locale_row.sort_order,
        }
    )
    assert ldto.displayName == "Tamil"
    assert ldto.sortOrder == 5


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #


def test_rbac_grants():
    assert has_permission(["super_admin"], "translation:manage")
    assert has_permission(["org_admin"], "translation:publish")
    assert has_permission(["communication_officer"], "translation:review")
    assert has_permission(["translator"], "translation:create")
    assert has_permission(["translator"], "translation:update")
    assert not has_permission(["translator"], "translation:publish")
    assert has_permission(["reviewer"], "translation:publish")
    assert not has_permission(["reviewer"], "translation:create")
    assert has_permission(["viewer"], "translation:view")
    assert not has_permission(["viewer"], "translation:create")
    assert has_permission(["volunteer"], "translation:view")
