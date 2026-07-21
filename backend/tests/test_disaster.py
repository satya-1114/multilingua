"""Unit tests for disaster repository & service layer.

Runs against SQLite in-memory. Postgres-specific column types on the
Disaster / Volunteer models are swapped for JSON — a test-only shim; nothing
under ``app/`` changes.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.disaster import (
    ASSIGNMENT_STATUS_ACCEPTED,
    ASSIGNMENT_STATUS_CANCELLED,
    ASSIGNMENT_STATUS_COMPLETED,
    ASSIGNMENT_STATUS_IN_PROGRESS,
    DISASTER_SEVERITY_HIGH,
    DISASTER_STATUS_ACTIVE,
    DISASTER_STATUS_CLOSED,
    DISASTER_STATUS_CONTAINED,
    DISASTER_STATUS_REPORTED,
    DISASTER_STATUS_RESOLVED,
    DISASTER_STATUS_VERIFIED,
    DISASTER_TYPE_FIRE,
    DISASTER_TYPE_FLOOD,
)
from app.constants.volunteer import VOLUNTEER_STATUS_INACTIVE
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.database.base import Base
from app.models.disaster import Disaster, DisasterAssignment, DisasterAttachment
from app.models.volunteer import Volunteer
from app.repositories.disaster import (
    disaster_assignments,
    disaster_attachments,
    disasters,
)
from app.repositories.volunteer import volunteers as volunteer_repo
from app.services import disaster as dsvc
from app.services import volunteer as vsvc


# --------------------------------------------------------------------------- #
# Test-only DB: swap Postgres types for SQLite-friendly ones and create tables.
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def sqlite_engine():
    from app.models.audit import AuditLog
    from app.models.campaign import Campaign
    from app.models.notification import Notification
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.volunteer import VolunteerTask

    for col_name in ("languages", "skills"):
        Volunteer.__table__.c[col_name].type = JSON()
    Campaign.__table__.c["channels"].type = JSON()
    AuditLog.__table__.c["metadata"].type = JSON()
    Disaster.__table__.c["metadata"].type = JSON()

    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
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
            DisasterAttachment.__table__,
            DisasterAssignment.__table__,
            Disaster.__table__,
            Volunteer.__table__,
        ):
            s.execute(tbl.delete())
        s.commit()
        s.close()


MANAGER_ROLES = ("campaign_manager",)  # has disaster:manage + assignment:manage
ACTOR_ROLES = ("volunteer",)  # has disaster:view + assignment:act
VIEWER_ROLES = ("viewer",)


def _make_volunteer(db, **overrides) -> Volunteer:
    payload = {
        "userId": overrides.pop("user_id", uuid.uuid4()),
        "languages": ["en"],
        "skills": ["outreach"],
        **overrides,
    }
    return vsvc.create_volunteer(db, roles=MANAGER_ROLES, payload=payload)


def _make_disaster(db, **overrides) -> Disaster:
    payload = {
        "title": overrides.pop("title", "Flood in Zone 3"),
        "disasterType": overrides.pop("disasterType", DISASTER_TYPE_FLOOD),
        "severity": overrides.pop("severity", DISASTER_SEVERITY_HIGH),
        **overrides,
    }
    return dsvc.create_disaster(
        db, roles=MANAGER_ROLES, created_by=uuid.uuid4(), payload=payload
    )


# ---------------------------- repository tests ----------------------------- #


class TestRepository:
    def test_search_pagination(self, db):
        for i in range(3):
            _make_disaster(db, title=f"D{i}")
        items, total = disasters.search(db, page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

    def test_get_by_status_and_type(self, db):
        d = _make_disaster(db)
        assert d in disasters.get_by_status(db, DISASTER_STATUS_REPORTED)
        assert d in disasters.get_by_type(db, DISASTER_TYPE_FLOOD)
        assert d in disasters.list_active(db)
        assert d in disasters.list_by_severity(db, DISASTER_SEVERITY_HIGH)

    def test_search_filters(self, db):
        _make_disaster(db, disasterType=DISASTER_TYPE_FIRE, city="Delhi")
        _make_disaster(db, disasterType=DISASTER_TYPE_FLOOD, city="Mumbai")
        items, total = disasters.search(db, disaster_type=DISASTER_TYPE_FIRE)
        assert total == 1
        assert items[0].city == "Delhi"
        items, total = disasters.search(db, city="mum")
        assert total == 1
        assert items[0].city == "Mumbai"

    def test_assignment_repo(self, db):
        d = _make_disaster(db)
        v = _make_volunteer(db)
        a = dsvc.assign_volunteer(
            db,
            roles=MANAGER_ROLES,
            assigned_by=None,
            disaster_id=d.id,
            payload={"volunteerId": v.id},
        )
        assert disaster_assignments.get_assignment(
            db, disaster_id=d.id, volunteer_id=v.id
        ).id == a.id
        assert a in disaster_assignments.list_by_disaster(db, d.id)
        assert a in disaster_assignments.list_by_volunteer(db, v.id)
        assert a in disaster_assignments.list_active(db, disaster_id=d.id)


# ------------------------ disaster service / state ------------------------ #


class TestDisasterService:
    def test_create_requires_permission(self, db):
        with pytest.raises(ForbiddenError):
            dsvc.create_disaster(
                db,
                roles=VIEWER_ROLES,
                created_by=None,
                payload={"title": "x", "disasterType": DISASTER_TYPE_FLOOD},
            )

    def test_invalid_type_rejected(self, db):
        with pytest.raises(ValidationError):
            _make_disaster(db, disasterType="alien_invasion")

    def test_invalid_severity_rejected(self, db):
        with pytest.raises(ValidationError):
            _make_disaster(db, severity="apocalyptic")

    def test_get_unknown_raises(self, db):
        with pytest.raises(NotFoundError):
            dsvc.get_disaster(db, roles=MANAGER_ROLES, disaster_id=uuid.uuid4())

    def test_full_lifecycle(self, db):
        d = _make_disaster(db)
        d = dsvc.verify_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        assert d.status == DISASTER_STATUS_VERIFIED
        d = dsvc.activate_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        assert d.status == DISASTER_STATUS_ACTIVE
        assert d.started_at is not None
        d = dsvc.contain_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        assert d.status == DISASTER_STATUS_CONTAINED
        d = dsvc.resolve_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        assert d.status == DISASTER_STATUS_RESOLVED
        assert d.resolved_at is not None
        d = dsvc.close_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        assert d.status == DISASTER_STATUS_CLOSED

    def test_illegal_transition(self, db):
        d = _make_disaster(db)  # reported
        with pytest.raises(ConflictError):
            dsvc.resolve_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)

    def test_reopen_only_from_resolved(self, db):
        d = _make_disaster(db)
        dsvc.verify_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        dsvc.activate_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        dsvc.resolve_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        reopened = dsvc.reopen_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        assert reopened.status == DISASTER_STATUS_ACTIVE
        assert reopened.resolved_at is None

    def test_cannot_edit_terminal(self, db):
        d = _make_disaster(db)
        d = dsvc.close_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        with pytest.raises(ConflictError):
            dsvc.update_disaster(
                db, roles=MANAGER_ROLES, disaster_id=d.id, payload={"title": "new"}
            )


# --------------------------- assignment service --------------------------- #


class TestAssignmentService:
    def test_assign_and_duplicate_conflicts(self, db):
        d = _make_disaster(db)
        v = _make_volunteer(db)
        dsvc.assign_volunteer(
            db,
            roles=MANAGER_ROLES,
            assigned_by=None,
            disaster_id=d.id,
            payload={"volunteerId": v.id, "role": "logistics"},
        )
        with pytest.raises(ConflictError):
            dsvc.assign_volunteer(
                db,
                roles=MANAGER_ROLES,
                assigned_by=None,
                disaster_id=d.id,
                payload={"volunteerId": v.id},
            )

    def test_cannot_assign_inactive_volunteer(self, db):
        d = _make_disaster(db)
        v = _make_volunteer(db)
        vsvc.deactivate(db, roles=MANAGER_ROLES, volunteer_id=v.id)
        with pytest.raises(ConflictError):
            dsvc.assign_volunteer(
                db,
                roles=MANAGER_ROLES,
                assigned_by=None,
                disaster_id=d.id,
                payload={"volunteerId": v.id},
            )

    def test_cannot_assign_to_resolved_disaster(self, db):
        d = _make_disaster(db)
        dsvc.verify_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        dsvc.activate_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        dsvc.resolve_disaster(db, roles=MANAGER_ROLES, disaster_id=d.id)
        v = _make_volunteer(db)
        with pytest.raises(ConflictError):
            dsvc.assign_volunteer(
                db,
                roles=MANAGER_ROLES,
                assigned_by=None,
                disaster_id=d.id,
                payload={"volunteerId": v.id},
            )

    def test_organization_mismatch(self, db):
        d_org = uuid.uuid4()
        v_org = uuid.uuid4()
        # organizations aren't inserted here — we set the FK directly to skip FK checks
        d = _make_disaster(db)
        d.organization_id = d_org
        db.commit()
        v = _make_volunteer(db)
        v.organization_id = v_org
        db.commit()
        with pytest.raises(ConflictError):
            dsvc.assign_volunteer(
                db,
                roles=MANAGER_ROLES,
                assigned_by=None,
                disaster_id=d.id,
                payload={"volunteerId": v.id},
            )

    def test_assignment_state_machine(self, db):
        d = _make_disaster(db)
        v = _make_volunteer(db)
        a = dsvc.assign_volunteer(
            db,
            roles=MANAGER_ROLES,
            assigned_by=None,
            disaster_id=d.id,
            payload={"volunteerId": v.id},
        )
        a = dsvc.change_assignment_status(
            db,
            roles=MANAGER_ROLES,
            actor_user_id=None,
            assignment_id=a.id,
            new_status=ASSIGNMENT_STATUS_ACCEPTED,
        )
        a = dsvc.change_assignment_status(
            db,
            roles=MANAGER_ROLES,
            actor_user_id=None,
            assignment_id=a.id,
            new_status=ASSIGNMENT_STATUS_IN_PROGRESS,
        )
        a = dsvc.complete_assignment(
            db, roles=MANAGER_ROLES, actor_user_id=None, assignment_id=a.id
        )
        assert a.status == ASSIGNMENT_STATUS_COMPLETED
        assert a.completed_at is not None

    def test_illegal_assignment_transition(self, db):
        d = _make_disaster(db)
        v = _make_volunteer(db)
        a = dsvc.assign_volunteer(
            db,
            roles=MANAGER_ROLES,
            assigned_by=None,
            disaster_id=d.id,
            payload={"volunteerId": v.id},
        )
        with pytest.raises(ConflictError):
            dsvc.complete_assignment(
                db, roles=MANAGER_ROLES, actor_user_id=None, assignment_id=a.id
            )

    def test_actor_can_only_act_on_own(self, db):
        d = _make_disaster(db)
        v = _make_volunteer(db)
        a = dsvc.assign_volunteer(
            db,
            roles=MANAGER_ROLES,
            assigned_by=None,
            disaster_id=d.id,
            payload={"volunteerId": v.id},
        )
        # Different user acting as volunteer role
        with pytest.raises(ForbiddenError):
            dsvc.change_assignment_status(
                db,
                roles=ACTOR_ROLES,
                actor_user_id=uuid.uuid4(),
                assignment_id=a.id,
                new_status=ASSIGNMENT_STATUS_ACCEPTED,
            )
        # Owner can accept
        a = dsvc.change_assignment_status(
            db,
            roles=ACTOR_ROLES,
            actor_user_id=v.user_id,
            assignment_id=a.id,
            new_status=ASSIGNMENT_STATUS_ACCEPTED,
        )
        assert a.status == ASSIGNMENT_STATUS_ACCEPTED

    def test_cancel_terminal_conflicts(self, db):
        d = _make_disaster(db)
        v = _make_volunteer(db)
        a = dsvc.assign_volunteer(
            db,
            roles=MANAGER_ROLES,
            assigned_by=None,
            disaster_id=d.id,
            payload={"volunteerId": v.id},
        )
        dsvc.cancel_assignment(db, roles=MANAGER_ROLES, assignment_id=a.id)
        with pytest.raises(ConflictError):
            dsvc.cancel_assignment(db, roles=MANAGER_ROLES, assignment_id=a.id)

    def test_reassign_to_new_volunteer(self, db):
        d = _make_disaster(db)
        v1 = _make_volunteer(db)
        v2 = _make_volunteer(db)
        a = dsvc.assign_volunteer(
            db,
            roles=MANAGER_ROLES,
            assigned_by=None,
            disaster_id=d.id,
            payload={"volunteerId": v1.id},
        )
        a = dsvc.reassign_volunteer(
            db,
            roles=MANAGER_ROLES,
            assigned_by=None,
            assignment_id=a.id,
            volunteer_id=v2.id,
        )
        assert a.volunteer_id == v2.id
        assert a.status == "assigned"


# ---------------------------- attachment service --------------------------- #


class TestAttachmentService:
    def test_register_and_remove(self, db):
        d = _make_disaster(db)
        att = dsvc.register_attachment(
            db,
            roles=MANAGER_ROLES,
            uploaded_by=None,
            disaster_id=d.id,
            payload={
                "kind": "image",
                "fileName": "flood.jpg",
                "fileUrl": "https://example.com/flood.jpg",
            },
        )
        assert att.file_name == "flood.jpg"
        assert att in dsvc.list_attachments(
            db, roles=MANAGER_ROLES, disaster_id=d.id
        )
        dsvc.remove_attachment(db, roles=MANAGER_ROLES, attachment_id=att.id)
        assert dsvc.list_attachments(db, roles=MANAGER_ROLES, disaster_id=d.id) == []

    def test_invalid_kind_rejected(self, db):
        d = _make_disaster(db)
        with pytest.raises(ValidationError):
            dsvc.register_attachment(
                db,
                roles=MANAGER_ROLES,
                uploaded_by=None,
                disaster_id=d.id,
                payload={
                    "kind": "hologram",
                    "fileName": "x",
                    "fileUrl": "https://example.com/x",
                },
            )

    def test_missing_fields_rejected(self, db):
        d = _make_disaster(db)
        with pytest.raises(ValidationError):
            dsvc.register_attachment(
                db,
                roles=MANAGER_ROLES,
                uploaded_by=None,
                disaster_id=d.id,
                payload={"kind": "image", "fileName": "only-name"},
            )
