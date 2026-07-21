"""Unit tests for volunteer repository & service layer.

Runs against SQLite in-memory (see ``conftest``). The ``Volunteer`` model
uses PostgreSQL ``ARRAY`` for ``languages`` / ``skills`` which SQLite cannot
create, so we build a minimal metadata subset with those columns swapped for
JSON — a test-only shim; nothing under ``app/`` changes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.volunteer import (
    TASK_STATUS_ACCEPTED,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_PENDING,
    TASK_STATUS_REJECTED,
    VOLUNTEER_STATUS_AVAILABLE,
    VOLUNTEER_STATUS_INACTIVE,
)
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.database.base import Base
from app.models.volunteer import Volunteer, VolunteerTask
from app.repositories.volunteer import volunteer_tasks, volunteers
from app.services import volunteer as vsvc


# --------------------------------------------------------------------------- #
# Test-only DB: rebuild Volunteer / VolunteerTask with SQLite-friendly types  #
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def sqlite_engine():
    from sqlalchemy import JSON

    from app.models.audit import AuditLog
    from app.models.campaign import Campaign
    from app.models.notification import Notification
    from app.models.organization import Organization
    from app.models.user import User

    # Swap ARRAY(String) → JSON on Volunteer/Campaign for SQLite compatibility.
    for col_name in ("languages", "skills"):
        Volunteer.__table__.c[col_name].type = JSON()
    Campaign.__table__.c["channels"].type = JSON()
    AuditLog.__table__.c["metadata"].type = JSON()

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
        # Cleanup between tests.
        s.rollback()
        for tbl in (VolunteerTask.__table__, Volunteer.__table__):
            s.execute(tbl.delete())
        s.commit()
        s.close()


MANAGER_ROLES = ("campaign_manager",)
ACTOR_ROLES = ("volunteer",)


def _make_volunteer(db, **overrides):
    payload = {
        "userId": overrides.pop("user_id", uuid.uuid4()),
        "languages": ["en"],
        "skills": ["outreach"],
        "status": VOLUNTEER_STATUS_AVAILABLE,
        **overrides,
    }
    return vsvc.create_volunteer(db, roles=MANAGER_ROLES, payload=payload)


# ---------------------------- repository tests ----------------------------- #

class TestRepository:
    def test_get_by_user_returns_none_for_unknown(self, db):
        assert volunteers.get_by_user(db, uuid.uuid4()) is None

    def test_get_by_user_and_status(self, db):
        v = _make_volunteer(db)
        assert volunteers.get_by_user(db, v.user_id).id == v.id
        assert v in volunteers.get_by_status(db, VOLUNTEER_STATUS_AVAILABLE)
        assert v in volunteers.list_available(db)

    def test_search_pagination(self, db):
        for _ in range(3):
            _make_volunteer(db)
        items, total = volunteers.search(db, page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

    def test_list_by_volunteer_and_assigned(self, db):
        v = _make_volunteer(db)
        t1 = vsvc.create_task(
            db,
            roles=MANAGER_ROLES,
            created_by=uuid.uuid4(),
            payload={"volunteerId": v.id, "title": "A"},
        )
        vsvc.change_status(
            db,
            roles=MANAGER_ROLES,
            actor_user_id=None,
            task_id=t1.id,
            new_status=TASK_STATUS_CANCELLED,
        )
        t2 = vsvc.create_task(
            db,
            roles=MANAGER_ROLES,
            created_by=uuid.uuid4(),
            payload={"volunteerId": v.id, "title": "B"},
        )
        active = volunteer_tasks.list_assigned(db, v.id)
        assert [t.id for t in active] == [t2.id]
        assert len(volunteer_tasks.list_by_volunteer(db, v.id)) == 2


# ---------------------------- service tests -------------------------------- #

class TestVolunteerService:
    def test_create_requires_permission(self, db):
        with pytest.raises(ForbiddenError):
            vsvc.create_volunteer(db, roles=("viewer",), payload={"userId": uuid.uuid4()})

    def test_duplicate_volunteer_conflicts(self, db):
        v = _make_volunteer(db)
        with pytest.raises(ConflictError):
            _make_volunteer(db, user_id=v.user_id)

    def test_invalid_status_rejected(self, db):
        with pytest.raises(ValidationError):
            _make_volunteer(db, status="ghost")

    def test_activate_and_deactivate(self, db):
        v = _make_volunteer(db)
        vsvc.deactivate(db, roles=MANAGER_ROLES, volunteer_id=v.id)
        assert volunteers.get(db, v.id).status == VOLUNTEER_STATUS_INACTIVE
        vsvc.activate(db, roles=MANAGER_ROLES, volunteer_id=v.id)
        assert volunteers.get(db, v.id).status == VOLUNTEER_STATUS_AVAILABLE

    def test_get_unknown_raises(self, db):
        with pytest.raises(NotFoundError):
            vsvc.get_volunteer(db, roles=MANAGER_ROLES, volunteer_id=uuid.uuid4())


class TestTaskService:
    def test_create_requires_task_assign(self, db):
        v = _make_volunteer(db)
        with pytest.raises(ForbiddenError):
            vsvc.create_task(
                db,
                roles=("viewer",),
                created_by=None,
                payload={"volunteerId": v.id, "title": "x"},
            )

    def test_create_rejects_inactive_volunteer(self, db):
        v = _make_volunteer(db, status=VOLUNTEER_STATUS_INACTIVE)
        with pytest.raises(ConflictError):
            vsvc.create_task(
                db,
                roles=MANAGER_ROLES,
                created_by=None,
                payload={"volunteerId": v.id, "title": "x"},
            )

    def test_due_in_past_rejected(self, db):
        v = _make_volunteer(db)
        past = datetime.now(timezone.utc) - timedelta(days=1)
        with pytest.raises(ValidationError):
            vsvc.create_task(
                db,
                roles=MANAGER_ROLES,
                created_by=None,
                payload={"volunteerId": v.id, "title": "x", "dueAt": past},
            )

    def test_full_actor_state_machine(self, db):
        v = _make_volunteer(db)
        task = vsvc.create_task(
            db,
            roles=MANAGER_ROLES,
            created_by=None,
            payload={"volunteerId": v.id, "title": "outreach"},
        )
        assert task.status == TASK_STATUS_PENDING

        # actor accepts → in_progress → completed
        step = lambda s: vsvc.change_status(  # noqa: E731
            db,
            roles=ACTOR_ROLES,
            actor_user_id=v.user_id,
            task_id=task.id,
            new_status=s,
        )
        assert step(TASK_STATUS_ACCEPTED).status == TASK_STATUS_ACCEPTED
        assert step(TASK_STATUS_IN_PROGRESS).status == TASK_STATUS_IN_PROGRESS
        done = step(TASK_STATUS_COMPLETED)
        assert done.status == TASK_STATUS_COMPLETED
        assert done.completed_at is not None

    def test_actor_cannot_skip_states(self, db):
        v = _make_volunteer(db)
        task = vsvc.create_task(
            db,
            roles=MANAGER_ROLES,
            created_by=None,
            payload={"volunteerId": v.id, "title": "x"},
        )
        with pytest.raises(ConflictError):
            vsvc.change_status(
                db,
                roles=ACTOR_ROLES,
                actor_user_id=v.user_id,
                task_id=task.id,
                new_status=TASK_STATUS_COMPLETED,
            )

    def test_actor_cannot_act_on_others_task(self, db):
        v = _make_volunteer(db)
        task = vsvc.create_task(
            db,
            roles=MANAGER_ROLES,
            created_by=None,
            payload={"volunteerId": v.id, "title": "x"},
        )
        with pytest.raises(ForbiddenError):
            vsvc.change_status(
                db,
                roles=ACTOR_ROLES,
                actor_user_id=uuid.uuid4(),
                task_id=task.id,
                new_status=TASK_STATUS_ACCEPTED,
            )

    def test_manager_can_force_cancel(self, db):
        v = _make_volunteer(db)
        task = vsvc.create_task(
            db,
            roles=MANAGER_ROLES,
            created_by=None,
            payload={"volunteerId": v.id, "title": "x"},
        )
        cancelled = vsvc.cancel_task(db, roles=MANAGER_ROLES, task_id=task.id)
        assert cancelled.status == TASK_STATUS_CANCELLED
        # Editing a terminal task now fails.
        with pytest.raises(ConflictError):
            vsvc.update_task(
                db, roles=MANAGER_ROLES, task_id=task.id, payload={"title": "y"}
            )

    def test_reassign_only_pending_or_accepted(self, db):
        v1 = _make_volunteer(db)
        v2 = _make_volunteer(db)
        task = vsvc.create_task(
            db,
            roles=MANAGER_ROLES,
            created_by=None,
            payload={"volunteerId": v1.id, "title": "x"},
        )
        moved = vsvc.reassign_task(
            db, roles=MANAGER_ROLES, task_id=task.id, volunteer_id=v2.id
        )
        assert moved.volunteer_id == v2.id
        vsvc.change_status(
            db,
            roles=MANAGER_ROLES,
            actor_user_id=None,
            task_id=task.id,
            new_status=TASK_STATUS_ACCEPTED,
        )
        vsvc.change_status(
            db,
            roles=MANAGER_ROLES,
            actor_user_id=None,
            task_id=task.id,
            new_status=TASK_STATUS_IN_PROGRESS,
        )
        with pytest.raises(ConflictError):
            vsvc.reassign_task(
                db, roles=MANAGER_ROLES, task_id=task.id, volunteer_id=v1.id
            )

    def test_list_my_tasks_empty_for_non_volunteer(self, db):
        assert (
            vsvc.list_my_tasks(
                db, roles=("campaign_manager", "volunteer"), user_id=uuid.uuid4()
            )
            == []
        )
