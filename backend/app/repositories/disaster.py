"""Repository layer for Disaster / DisasterAssignment / DisasterAttachment.

Thin extensions over :class:`CRUDBase`. Business rules (validation,
state-machine transitions, permission checks) live in
:mod:`app.services.disaster`, not here.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants.disaster import (
    ASSIGNMENT_STATUSES_TERMINAL,
    DISASTER_STATUSES_OPEN,
)
from app.crud.base import CRUDBase
from app.models.disaster import Disaster, DisasterAssignment, DisasterAttachment


class DisasterRepository(CRUDBase[Disaster]):
    def __init__(self) -> None:
        super().__init__(Disaster)

    # -- simple reads --------------------------------------------------------
    def get_by_status(
        self, db: Session, status: str, *, limit: int | None = None
    ) -> list[Disaster]:
        stmt = select(Disaster).where(
            Disaster.status == status, Disaster.deleted_at.is_(None)
        )
        if limit:
            stmt = stmt.limit(limit)
        return list(db.scalars(stmt))

    def get_by_type(self, db: Session, disaster_type: str) -> list[Disaster]:
        stmt = select(Disaster).where(
            Disaster.disaster_type == disaster_type,
            Disaster.deleted_at.is_(None),
        )
        return list(db.scalars(stmt))

    def list_active(self, db: Session) -> list[Disaster]:
        stmt = (
            select(Disaster)
            .where(
                Disaster.status.in_(list(DISASTER_STATUSES_OPEN)),
                Disaster.deleted_at.is_(None),
            )
            .order_by(Disaster.created_at.desc())
        )
        return list(db.scalars(stmt))

    def list_by_organization(
        self, db: Session, organization_id: uuid.UUID | str
    ) -> list[Disaster]:
        stmt = select(Disaster).where(
            Disaster.organization_id == organization_id,
            Disaster.deleted_at.is_(None),
        )
        return list(db.scalars(stmt))

    def list_by_severity(self, db: Session, severity: str) -> list[Disaster]:
        stmt = select(Disaster).where(
            Disaster.severity == severity, Disaster.deleted_at.is_(None)
        )
        return list(db.scalars(stmt))

    # -- rich search ---------------------------------------------------------
    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
        disaster_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        organization_id: uuid.UUID | str | None = None,
        city: str | None = None,
        district: str | None = None,
        state: str | None = None,
        country: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        volunteer_id: uuid.UUID | str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[Disaster], int]:
        stmt = select(Disaster).where(Disaster.deleted_at.is_(None))
        if disaster_type:
            stmt = stmt.where(Disaster.disaster_type == disaster_type)
        if severity:
            stmt = stmt.where(Disaster.severity == severity)
        if status:
            stmt = stmt.where(Disaster.status == status)
        if organization_id:
            stmt = stmt.where(Disaster.organization_id == organization_id)
        if city:
            stmt = stmt.where(Disaster.city.ilike(f"%{city}%"))
        if district:
            stmt = stmt.where(Disaster.district.ilike(f"%{district}%"))
        if state:
            stmt = stmt.where(Disaster.state.ilike(f"%{state}%"))
        if country:
            stmt = stmt.where(Disaster.country.ilike(f"%{country}%"))
        if started_from:
            stmt = stmt.where(Disaster.started_at >= started_from)
        if started_to:
            stmt = stmt.where(Disaster.started_at <= started_to)
        if volunteer_id:
            sub = (
                select(DisasterAssignment.disaster_id)
                .where(
                    DisasterAssignment.volunteer_id == volunteer_id,
                    DisasterAssignment.deleted_at.is_(None),
                )
                .subquery()
            )
            stmt = stmt.where(Disaster.id.in_(select(sub)))
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Disaster.title.ilike(like),
                    Disaster.description.ilike(like),
                    Disaster.address.ilike(like),
                    Disaster.city.ilike(like),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(Disaster, sort_by):
            col = getattr(Disaster, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(Disaster.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)


class DisasterAssignmentRepository(CRUDBase[DisasterAssignment]):
    def __init__(self) -> None:
        super().__init__(DisasterAssignment)

    def list_by_disaster(
        self,
        db: Session,
        disaster_id: uuid.UUID | str,
        *,
        statuses: Sequence[str] | None = None,
    ) -> list[DisasterAssignment]:
        stmt = select(DisasterAssignment).where(
            DisasterAssignment.disaster_id == disaster_id,
            DisasterAssignment.deleted_at.is_(None),
        )
        if statuses:
            stmt = stmt.where(DisasterAssignment.status.in_(list(statuses)))
        return list(db.scalars(stmt.order_by(DisasterAssignment.created_at.desc())))

    def list_by_volunteer(
        self,
        db: Session,
        volunteer_id: uuid.UUID | str,
        *,
        statuses: Sequence[str] | None = None,
    ) -> list[DisasterAssignment]:
        stmt = select(DisasterAssignment).where(
            DisasterAssignment.volunteer_id == volunteer_id,
            DisasterAssignment.deleted_at.is_(None),
        )
        if statuses:
            stmt = stmt.where(DisasterAssignment.status.in_(list(statuses)))
        return list(db.scalars(stmt.order_by(DisasterAssignment.created_at.desc())))

    def list_active(
        self, db: Session, *, disaster_id: uuid.UUID | str | None = None
    ) -> list[DisasterAssignment]:
        active = tuple(
            s for s in ("assigned", "accepted", "in_progress")
            if s not in ASSIGNMENT_STATUSES_TERMINAL
        )
        stmt = select(DisasterAssignment).where(
            DisasterAssignment.status.in_(list(active)),
            DisasterAssignment.deleted_at.is_(None),
        )
        if disaster_id:
            stmt = stmt.where(DisasterAssignment.disaster_id == disaster_id)
        return list(db.scalars(stmt.order_by(DisasterAssignment.created_at.desc())))

    def get_assignment(
        self,
        db: Session,
        *,
        disaster_id: uuid.UUID | str,
        volunteer_id: uuid.UUID | str,
    ) -> DisasterAssignment | None:
        stmt = select(DisasterAssignment).where(
            DisasterAssignment.disaster_id == disaster_id,
            DisasterAssignment.volunteer_id == volunteer_id,
            DisasterAssignment.deleted_at.is_(None),
        )
        return db.scalar(stmt)


class DisasterAttachmentRepository(CRUDBase[DisasterAttachment]):
    def __init__(self) -> None:
        super().__init__(DisasterAttachment)

    def list_by_disaster(
        self, db: Session, disaster_id: uuid.UUID | str, *, kind: str | None = None
    ) -> list[DisasterAttachment]:
        stmt = select(DisasterAttachment).where(
            DisasterAttachment.disaster_id == disaster_id,
            DisasterAttachment.deleted_at.is_(None),
        )
        if kind:
            stmt = stmt.where(DisasterAttachment.kind == kind)
        return list(db.scalars(stmt.order_by(DisasterAttachment.created_at.desc())))


disasters = DisasterRepository()
disaster_assignments = DisasterAssignmentRepository()
disaster_attachments = DisasterAttachmentRepository()


__all__ = [
    "DisasterRepository",
    "DisasterAssignmentRepository",
    "DisasterAttachmentRepository",
    "disasters",
    "disaster_assignments",
    "disaster_attachments",
]
