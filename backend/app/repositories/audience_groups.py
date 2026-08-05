"""Repository helpers for audience groups and their membership links."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.audience import Audience, AudienceGroup, AudienceGroupMember

groups = CRUDBase(AudienceGroup)


def list_groups(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
    workspace_id: str | None = None,
) -> tuple[list[AudienceGroup], int]:
    return groups.list(
        db,
        page=page,
        page_size=page_size,
        search=search,
        search_fields=["name", "description"],
        filters={"workspace_id": workspace_id},
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def get_group(db: Session, group_id: Any) -> AudienceGroup | None:
    return groups.get(db, group_id)


def create_group(db: Session, data: dict[str, Any]) -> AudienceGroup:
    return groups.create(db, data)


def update_group(db: Session, obj: AudienceGroup, data: dict[str, Any]) -> AudienceGroup:
    return groups.update(db, obj, data)


def delete_group(db: Session, obj: AudienceGroup) -> None:
    groups.soft_delete(db, obj)


def add_members(
    db: Session,
    group_id: Any,
    audience_ids: list[str],
) -> tuple[int, int]:
    """Link contacts to a group. Revives soft-deleted links, skips duplicates."""

    group = get_group(db, group_id)

    if not group:
        return 0, len(audience_ids)

    added = 0
    skipped = 0

    for audience_id in dict.fromkeys(audience_ids):

        contact = db.scalar(
            select(Audience).where(
                Audience.id == audience_id,
                Audience.deleted_at.is_(None),
            )
        )

        if not contact:
            skipped += 1
            continue

        link = db.scalar(
            select(AudienceGroupMember).where(
                AudienceGroupMember.group_id == group.id,
                AudienceGroupMember.audience_id == audience_id,
            )
        )

        if link is None:
            db.add(
                AudienceGroupMember(
                    workspace_id=group.workspace_id,
                    group_id=group.id,
                    audience_id=audience_id,
                )
            )
            added += 1

        elif link.deleted_at is not None:
            link.deleted_at = None
            added += 1

        else:
            skipped += 1

    db.commit()

    return added, skipped


def remove_member(db: Session, group_id: Any, audience_id: Any) -> bool:
    link = db.scalar(
        select(AudienceGroupMember).where(
            AudienceGroupMember.group_id == group_id,
            AudienceGroupMember.audience_id == audience_id,
            AudienceGroupMember.deleted_at.is_(None),
        )
    )
    if not link:
        return False
    link.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def list_members(
    db: Session,
    group_id: Any,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
) -> tuple[list[Audience], int]:
    stmt = (
        select(Audience)
        .join(AudienceGroupMember, AudienceGroupMember.audience_id == Audience.id)
        .where(
            AudienceGroupMember.group_id == group_id,
            AudienceGroupMember.deleted_at.is_(None),
            Audience.deleted_at.is_(None),
        )
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Audience.full_name.ilike(like),
                Audience.email.ilike(like),
                Audience.phone.ilike(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Audience.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), int(total)


def member_count(db: Session, group_id: Any) -> int:
    stmt = (
        select(func.count(AudienceGroupMember.id))
        .join(Audience, AudienceGroupMember.audience_id == Audience.id)
        .where(
            AudienceGroupMember.group_id == group_id,
            AudienceGroupMember.deleted_at.is_(None),
            Audience.deleted_at.is_(None),
        )
    )
    return int(db.scalar(stmt) or 0)