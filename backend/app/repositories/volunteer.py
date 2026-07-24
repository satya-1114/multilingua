"""Repository layer for Volunteer & VolunteerTask.

Thin extensions over :class:`CRUDBase` with only the reusable, query-shape
helpers the service layer needs. Anything with business rules (validation,
state-machine transitions, permission enforcement) belongs in the service
layer, not here.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants.volunteer import (
    TASK_STATUSES,
    VOLUNTEER_STATUS_AVAILABLE,
)
from app.crud.base import CRUDBase
from app.models.volunteer import Volunteer, VolunteerTask


class VolunteerRepository(CRUDBase[Volunteer]):
    def __init__(self) -> None:
        super().__init__(Volunteer)

    # -- reads ----------------------------------------------------------------
    def get_by_user(self, db: Session, user_id: uuid.UUID | str) -> Volunteer | None:
        stmt = select(Volunteer).where(Volunteer.user_id == user_id)
        if hasattr(Volunteer, "deleted_at"):
            stmt = stmt.where(Volunteer.deleted_at.is_(None))
        return db.scalar(stmt)

    def get_by_status(
        self, db: Session, status: str, *, limit: int | None = None
    ) -> list[Volunteer]:
        stmt = select(Volunteer).where(
            Volunteer.status == status, Volunteer.deleted_at.is_(None)
        )
        if limit:
            stmt = stmt.limit(limit)
        return list(db.scalars(stmt))

    def list_by_organization(
        self, db: Session, organization_id: uuid.UUID | str
    ) -> list[Volunteer]:
        stmt = select(Volunteer).where(
            Volunteer.organization_id == organization_id,
            Volunteer.deleted_at.is_(None),
        )
        return list(db.scalars(stmt))

    def list_available(self, db: Session) -> list[Volunteer]:
        return self.get_by_status(db, VOLUNTEER_STATUS_AVAILABLE)

    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
        language: str | None = None,
        skill: str | None = None,
        location: str | None = None,
        availability: str | None = None,
        status: str | None = None,
        organization_id: uuid.UUID | str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[Volunteer], int]:
        stmt = select(Volunteer).where(Volunteer.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Volunteer.status == status)
        if availability:
            stmt = stmt.where(Volunteer.availability == availability)
        if organization_id:
            stmt = stmt.where(Volunteer.organization_id == organization_id)
        if location:
            stmt = stmt.where(Volunteer.current_location.ilike(f"%{location}%"))
        if language:
            stmt = stmt.where(Volunteer.languages.any(language))
        if skill:
            stmt = stmt.where(Volunteer.skills.any(skill))
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Volunteer.current_location.ilike(like),
                    Volunteer.availability.ilike(like),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(Volunteer, sort_by):
            col = getattr(Volunteer, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(Volunteer.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)


class VolunteerTaskRepository(CRUDBase[VolunteerTask]):
    def __init__(self) -> None:
        super().__init__(VolunteerTask)

    def list_by_volunteer(
        self,
        db: Session,
        volunteer_id: uuid.UUID | str,
        *,
        statuses: Sequence[str] | None = None,
    ) -> list[VolunteerTask]:
        stmt = select(VolunteerTask).where(
            VolunteerTask.volunteer_id == volunteer_id,
            VolunteerTask.deleted_at.is_(None),
        )
        if statuses:
            stmt = stmt.where(VolunteerTask.status.in_(list(statuses)))
        stmt = stmt.order_by(VolunteerTask.created_at.desc())
        return list(db.scalars(stmt))

    def list_by_campaign(
        self, db: Session, campaign_id: uuid.UUID | str
    ) -> list[VolunteerTask]:
        stmt = (
            select(VolunteerTask)
            .where(
                VolunteerTask.campaign_id == campaign_id,
                VolunteerTask.deleted_at.is_(None),
            )
            .order_by(VolunteerTask.created_at.desc())
        )
        return list(db.scalars(stmt))

    def list_assigned(
        self, db: Session, volunteer_id: uuid.UUID | str
    ) -> list[VolunteerTask]:
        """Non-terminal tasks currently on a volunteer's plate."""
        from app.constants.volunteer import TASK_STATUSES_TERMINAL

        active = tuple(s for s in TASK_STATUSES if s not in TASK_STATUSES_TERMINAL)
        return self.list_by_volunteer(db, volunteer_id, statuses=active)

    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        volunteer_id: uuid.UUID | str | None = None,
        campaign_id: uuid.UUID | str | None = None,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
    ) -> tuple[list[VolunteerTask], int]:
        stmt = select(VolunteerTask).where(VolunteerTask.deleted_at.is_(None))
        if volunteer_id:
            stmt = stmt.where(VolunteerTask.volunteer_id == volunteer_id)
        if campaign_id:
            stmt = stmt.where(VolunteerTask.campaign_id == campaign_id)
        if status:
            stmt = stmt.where(VolunteerTask.status == status)
        if priority:
            stmt = stmt.where(VolunteerTask.priority == priority)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    VolunteerTask.title.ilike(like),
                    VolunteerTask.description.ilike(like),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(VolunteerTask.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        return list(db.scalars(stmt)), int(total)


volunteers = VolunteerRepository()
volunteer_tasks = VolunteerTaskRepository()


__all__ = [
    "VolunteerRepository",
    "VolunteerTaskRepository",
    "volunteers",
    "volunteer_tasks",
]
