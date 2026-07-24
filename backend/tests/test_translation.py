"""Repository & service tests for the multilingual platform (Phase 5.2).

SQLite in-memory; Postgres JSONB columns are swapped for JSON so tables
build. Mirrors the fixture style used by ``tests/test_public_access.py``.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.translation import (
    JOB_STATUS_CANCELLED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_PENDING,
    JOB_STATUS_PROCESSING,
    TRANSLATION_STATUS_DRAFT,
    TRANSLATION_STATUS_PUBLISHED,
    TRANSLATION_STATUS_REVIEWED,
    TRANSLATION_STATUS_TRANSLATED,
)
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.models.translation import Translation, TranslationJob, TranslationLocale
from app.repositories.translation import (
    translations as tr_repo,
)
from app.services import translation as svc


MANAGER_ROLES = ("super_admin",)  # translation:*
REVIEWER_ROLES = ("reviewer",)
TRANSLATOR_ROLES = ("translator",)
VIEWER_ROLES = ("viewer",)  # translation:view only
VOLUNTEER_ROLES = ("volunteer",)  # translation:view only


# --------------------------------------------------------------------------- #
# Test DB — SQLite w/ JSONB swap
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def sqlite_engine():
    from app.models.user import User  # register FK target

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
            Translation.__table__,
            TranslationJob.__table__,
            TranslationLocale.__table__,
        ):
            s.execute(tbl.delete())
        s.commit()
        s.close()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _mk_translation(db, **overrides):
    payload = {
        "entity_type": "disaster",
        "entity_id": uuid.uuid4(),
        "locale": "hi",
        "field_name": "title",
        "translated_value": "प्रलय",
    }
    payload.update(overrides)
    return svc.create_translation(db, roles=MANAGER_ROLES, payload=payload)


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #


def test_repository_upsert(db):
    eid = uuid.uuid4()
    row, created = tr_repo.upsert_translation(
        db,
        entity_type="disaster",
        entity_id=eid,
        locale="ta",
        field_name="title",
        defaults={"translated_value": "தலைப்பு", "status": "draft"},
    )
    assert created is True
    assert row.translated_value == "தலைப்பு"

    row2, created2 = tr_repo.upsert_translation(
        db,
        entity_type="disaster",
        entity_id=eid,
        locale="ta",
        field_name="title",
        defaults={"translated_value": "புதிய"},
    )
    assert created2 is False
    assert row2.id == row.id
    assert row2.translated_value == "புதிய"


def test_repository_list_and_search(db):
    eid = uuid.uuid4()
    _mk_translation(db, entity_id=eid, locale="hi", field_name="title")
    _mk_translation(db, entity_id=eid, locale="ta", field_name="title")
    _mk_translation(db, entity_id=eid, locale="hi", field_name="body")

    all_for_entity = tr_repo.list_by_entity(
        db, entity_type="disaster", entity_id=eid
    )
    assert len(all_for_entity) == 3

    hi_only = tr_repo.list_by_entity(
        db, entity_type="disaster", entity_id=eid, locale="hi"
    )
    assert {t.field_name for t in hi_only} == {"title", "body"}

    rows, total = tr_repo.search(
        db, entity_type="disaster", locale="hi", page=1, page_size=10
    )
    assert total == 2
    assert all(r.locale == "hi" for r in rows)


def test_repository_published_lookup(db):
    row = _mk_translation(db)
    # walk it through the workflow
    row = svc.update_translation(
        db,
        roles=MANAGER_ROLES,
        translation_id=row.id,
        payload={"status": TRANSLATION_STATUS_TRANSLATED},
    )
    row = svc.review_translation(
        db,
        roles=MANAGER_ROLES,
        translation_id=row.id,
        reviewer_id=uuid.uuid4(),
    )
    row = svc.publish_translation(
        db, roles=MANAGER_ROLES, translation_id=row.id
    )

    hit = tr_repo.published_translation(
        db,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        locale=row.locale,
        field_name=row.field_name,
    )
    assert hit is not None
    assert hit.status == TRANSLATION_STATUS_PUBLISHED


# --------------------------------------------------------------------------- #
# Service — validation
# --------------------------------------------------------------------------- #


def test_create_rejects_missing_fields(db):
    with pytest.raises(ValidationError):
        svc.create_translation(
            db,
            roles=MANAGER_ROLES,
            payload={"entity_type": "disaster", "entity_id": uuid.uuid4()},
        )


def test_create_rejects_invalid_entity_type(db):
    with pytest.raises(ValidationError):
        svc.create_translation(
            db,
            roles=MANAGER_ROLES,
            payload={
                "entity_type": "unknown",
                "entity_id": uuid.uuid4(),
                "locale": "hi",
                "field_name": "title",
            },
        )


def test_create_rejects_duplicate_scope(db):
    row = _mk_translation(db)
    with pytest.raises(ConflictError):
        svc.create_translation(
            db,
            roles=MANAGER_ROLES,
            payload={
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "locale": row.locale,
                "field_name": row.field_name,
                "translated_value": "dup",
            },
        )


def test_create_rejects_non_draft_without_value(db):
    with pytest.raises(ValidationError):
        svc.create_translation(
            db,
            roles=MANAGER_ROLES,
            payload={
                "entity_type": "disaster",
                "entity_id": uuid.uuid4(),
                "locale": "hi",
                "field_name": "title",
                "status": TRANSLATION_STATUS_TRANSLATED,
                "translated_value": "   ",
            },
        )


# --------------------------------------------------------------------------- #
# Service — permissions
# --------------------------------------------------------------------------- #


def test_view_permission_required(db):
    with pytest.raises(ForbiddenError):
        svc.get_entity_translations(
            db,
            roles=("no_such_role",),
            entity_type="disaster",
            entity_id=uuid.uuid4(),
        )


def test_publish_permission_required(db):
    row = _mk_translation(db)
    row = svc.update_translation(
        db,
        roles=MANAGER_ROLES,
        translation_id=row.id,
        payload={"status": TRANSLATION_STATUS_TRANSLATED},
    )
    row = svc.review_translation(
        db, roles=MANAGER_ROLES, translation_id=row.id, reviewer_id=uuid.uuid4()
    )
    with pytest.raises(ForbiddenError):
        svc.publish_translation(
            db, roles=TRANSLATOR_ROLES, translation_id=row.id
        )


def test_translator_can_create_but_not_publish(db):
    row = svc.create_translation(
        db,
        roles=TRANSLATOR_ROLES,
        payload={
            "entity_type": "campaign",
            "entity_id": uuid.uuid4(),
            "locale": "hi",
            "field_name": "title",
            "translated_value": "hello",
            "status": TRANSLATION_STATUS_TRANSLATED,
        },
    )
    with pytest.raises(ForbiddenError):
        svc.review_translation(
            db, roles=TRANSLATOR_ROLES, translation_id=row.id, reviewer_id=uuid.uuid4()
        )


def test_viewer_cannot_create(db):
    with pytest.raises(ForbiddenError):
        _mk_translation(db, entity_id=uuid.uuid4())  # uses MANAGER_ROLES
        svc.create_translation(
            db,
            roles=VIEWER_ROLES,
            payload={
                "entity_type": "disaster",
                "entity_id": uuid.uuid4(),
                "locale": "hi",
                "field_name": "title",
                "translated_value": "x",
            },
        )


# --------------------------------------------------------------------------- #
# Service — workflow transitions
# --------------------------------------------------------------------------- #


def test_workflow_happy_path(db):
    row = _mk_translation(db)
    assert row.status == TRANSLATION_STATUS_DRAFT

    row = svc.update_translation(
        db,
        roles=MANAGER_ROLES,
        translation_id=row.id,
        payload={"status": TRANSLATION_STATUS_TRANSLATED},
    )
    assert row.status == TRANSLATION_STATUS_TRANSLATED

    reviewer = uuid.uuid4()
    row = svc.review_translation(
        db, roles=MANAGER_ROLES, translation_id=row.id, reviewer_id=reviewer
    )
    assert row.status == TRANSLATION_STATUS_REVIEWED
    assert row.reviewed_by_user_id == reviewer

    row = svc.publish_translation(
        db, roles=MANAGER_ROLES, translation_id=row.id
    )
    assert row.status == TRANSLATION_STATUS_PUBLISHED


def test_cannot_publish_draft(db):
    row = _mk_translation(db)
    with pytest.raises(ConflictError):
        svc.publish_translation(
            db, roles=MANAGER_ROLES, translation_id=row.id
        )


def test_cannot_skip_review(db):
    row = _mk_translation(db)
    row = svc.update_translation(
        db,
        roles=MANAGER_ROLES,
        translation_id=row.id,
        payload={"status": TRANSLATION_STATUS_TRANSLATED},
    )
    with pytest.raises(ConflictError):
        svc.update_translation(
            db,
            roles=MANAGER_ROLES,
            translation_id=row.id,
            payload={"status": TRANSLATION_STATUS_PUBLISHED},
        )


def test_review_rejection_resets_to_draft(db):
    row = _mk_translation(db)
    row = svc.update_translation(
        db,
        roles=MANAGER_ROLES,
        translation_id=row.id,
        payload={"status": TRANSLATION_STATUS_TRANSLATED},
    )
    row = svc.review_translation(
        db,
        roles=MANAGER_ROLES,
        translation_id=row.id,
        reviewer_id=uuid.uuid4(),
        approve=False,
    )
    assert row.status == TRANSLATION_STATUS_DRAFT
    assert row.reviewed_by_user_id is None


def test_delete_soft_deletes(db):
    row = _mk_translation(db)
    svc.delete_translation(db, roles=MANAGER_ROLES, translation_id=row.id)
    assert tr_repo.get_translation(db, row.id) is None


# --------------------------------------------------------------------------- #
# Service — job lifecycle
# --------------------------------------------------------------------------- #


def test_job_lifecycle(db):
    job = svc.request_translation(
        db,
        roles=MANAGER_ROLES,
        requested_by=uuid.uuid4(),
        payload={
            "entity_type": "disaster",
            "entity_id": uuid.uuid4(),
            "source_locale": "en",
            "target_locale": "hi",
            "provider": "ai",
        },
    )
    assert job.status == JOB_STATUS_PENDING

    job = svc.start_job(db, roles=MANAGER_ROLES, job_id=job.id)
    assert job.status == JOB_STATUS_PROCESSING

    job = svc.complete_job(
        db, roles=MANAGER_ROLES, job_id=job.id, metadata={"chars": 42}
    )
    assert job.status == JOB_STATUS_COMPLETED
    assert job.metadata_["chars"] == 42


def test_job_rejects_same_locale(db):
    with pytest.raises(ValidationError):
        svc.request_translation(
            db,
            roles=MANAGER_ROLES,
            requested_by=None,
            payload={
                "entity_type": "campaign",
                "entity_id": uuid.uuid4(),
                "source_locale": "en",
                "target_locale": "en",
            },
        )


def test_job_cancel_and_illegal_transition(db):
    job = svc.request_translation(
        db,
        roles=MANAGER_ROLES,
        requested_by=None,
        payload={
            "entity_type": "campaign",
            "entity_id": uuid.uuid4(),
            "source_locale": "en",
            "target_locale": "hi",
        },
    )
    job = svc.cancel_job(db, roles=MANAGER_ROLES, job_id=job.id)
    assert job.status == JOB_STATUS_CANCELLED
    with pytest.raises(ConflictError):
        svc.start_job(db, roles=MANAGER_ROLES, job_id=job.id)


def test_job_fail_records_error(db):
    job = svc.request_translation(
        db,
        roles=MANAGER_ROLES,
        requested_by=None,
        payload={
            "entity_type": "campaign",
            "entity_id": uuid.uuid4(),
            "source_locale": "en",
            "target_locale": "hi",
        },
    )
    job = svc.fail_job(
        db, roles=MANAGER_ROLES, job_id=job.id, error="provider timeout"
    )
    assert job.status == JOB_STATUS_FAILED
    assert job.metadata_.get("error") == "provider timeout"


# --------------------------------------------------------------------------- #
# Service — locale management
# --------------------------------------------------------------------------- #


def test_register_and_default_locale(db):
    en = svc.register_locale(
        db,
        roles=MANAGER_ROLES,
        payload={"locale": "en", "display_name": "English"},
    )
    hi = svc.register_locale(
        db,
        roles=MANAGER_ROLES,
        payload={"locale": "hi", "display_name": "Hindi"},
    )
    assert en.enabled is True

    hi = svc.set_default_locale(db, roles=MANAGER_ROLES, locale="hi")
    assert hi.default_locale is True
    assert svc.get_default_locale(db).locale == "hi"

    # only one default
    en = svc.set_default_locale(db, roles=MANAGER_ROLES, locale="en")
    assert svc.get_default_locale(db).locale == "en"

    # duplicate register
    with pytest.raises(ConflictError):
        svc.register_locale(
            db,
            roles=MANAGER_ROLES,
            payload={"locale": "en", "display_name": "English"},
        )


def test_cannot_disable_default_locale(db):
    svc.register_locale(
        db, roles=MANAGER_ROLES, payload={"locale": "en", "display_name": "English"}
    )
    svc.set_default_locale(db, roles=MANAGER_ROLES, locale="en")
    with pytest.raises(ConflictError):
        svc.disable_locale(db, roles=MANAGER_ROLES, locale="en")


def test_create_translation_requires_registered_locale(db):
    svc.register_locale(
        db, roles=MANAGER_ROLES, payload={"locale": "hi", "display_name": "Hindi"}
    )
    # 'zz' is not registered — should be rejected once the registry is non-empty.
    with pytest.raises(ValidationError):
        svc.create_translation(
            db,
            roles=MANAGER_ROLES,
            payload={
                "entity_type": "disaster",
                "entity_id": uuid.uuid4(),
                "locale": "zz",
                "field_name": "title",
                "translated_value": "x",
            },
        )


def test_disable_locale_blocks_new_translations(db):
    svc.register_locale(
        db, roles=MANAGER_ROLES, payload={"locale": "hi", "display_name": "Hindi"}
    )
    svc.register_locale(
        db,
        roles=MANAGER_ROLES,
        payload={"locale": "ta", "display_name": "Tamil"},
    )
    svc.set_default_locale(db, roles=MANAGER_ROLES, locale="hi")
    svc.disable_locale(db, roles=MANAGER_ROLES, locale="ta")

    with pytest.raises(ConflictError):
        svc.create_translation(
            db,
            roles=MANAGER_ROLES,
            payload={
                "entity_type": "disaster",
                "entity_id": uuid.uuid4(),
                "locale": "ta",
                "field_name": "title",
                "translated_value": "x",
            },
        )


def test_disable_missing_locale_404(db):
    with pytest.raises(NotFoundError):
        svc.disable_locale(db, roles=MANAGER_ROLES, locale="xx")


# --------------------------------------------------------------------------- #
# Search + filters
# --------------------------------------------------------------------------- #


def test_search_filters_and_query(db):
    eid = uuid.uuid4()
    _mk_translation(
        db, entity_id=eid, locale="hi", field_name="title", translated_value="प्रलय"
    )
    _mk_translation(
        db, entity_id=eid, locale="hi", field_name="body", translated_value="विवरण"
    )
    _mk_translation(
        db,
        entity_id=uuid.uuid4(),
        locale="ta",
        field_name="title",
        translated_value="தலைப்பு",
    )

    rows, total = svc.search_translations(
        db,
        roles=MANAGER_ROLES,
        filters={"entity_type": "disaster", "locale": "hi"},
    )
    assert total == 2

    rows, total = svc.search_translations(
        db,
        roles=MANAGER_ROLES,
        filters={"entity_type": "disaster", "query": "प्रलय"},
    )
    assert total == 1
    assert rows[0].translated_value == "प्रलय"


def test_search_rejects_bad_status(db):
    with pytest.raises(ValidationError):
        svc.search_translations(
            db, roles=MANAGER_ROLES, filters={"status": "approved"}
        )
