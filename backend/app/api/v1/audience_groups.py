from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.audience import Audience, AudienceGroup
from app.models.user import User
from app.repositories import audience_groups
from app.schemas.audience_group import (
    AddMembersRequest,
    AudienceGroupCreate,
    AudienceGroupUpdate,
)
from app.services import audit

router = APIRouter()


def _serialize(group: AudienceGroup, member_count: int = 0) -> dict:
    return {
        "id": str(group.id),
        "workspaceId": str(group.workspace_id),
        "name": group.name,
        "description": group.description,
        "memberCount": member_count,
        "createdAt": group.created_at.isoformat(),
        "updatedAt": group.updated_at.isoformat(),
        "deletedAt": group.deleted_at.isoformat() if group.deleted_at else None,
    }


def _serialize_member(audience: Audience) -> dict:
    return {
        "id": str(audience.id),
        "workspaceId": str(audience.workspace_id),
        "fullName": audience.full_name,
        "email": audience.email,
        "phone": audience.phone,
        "language": audience.language,
        "tags": audience.tags or [],
        "status": audience.status,
        "district": audience.district,
        "state": audience.state,
        "createdAt": audience.created_at.isoformat(),
        "updatedAt": audience.updated_at.isoformat(),
    }


def _from_camel(data: dict) -> dict:
    if "workspaceId" in data:
        data["workspace_id"] = data.pop("workspaceId")
    return data


def _audit(
    db: Session,
    request: Request,
    user: User,
    action: str,
    obj: AudienceGroup,
    metadata: dict | None = None,
) -> None:
    audit.log(
        db,
        action=action,
        module="audience_group",
        actor_id=user.id,
        workspace_id=getattr(obj, "workspace_id", None),
        entity_id=str(getattr(obj, "id", "")),
        entity_label=getattr(obj, "name", None),
        ip=request.client.host if request.client else None,
        ua=request.headers.get("user-agent"),
        metadata=metadata,
    )


@router.get("")
def list_(
    workspaceId: str | None = None,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("audience:view")),
):
    items, total = audience_groups.list_groups(
        db,
        page=pp.page,
        page_size=pp.page_size,
        search=pp.search,
        sort_by=pp.sort_by,
        sort_dir=pp.sort_dir,
        workspace_id=workspaceId,
    )

    data = [
        _serialize(group, audience_groups.member_count(db, group.id))
        for group in items
    ]

    return paginated(data, pp.page, pp.page_size, total)


@router.post("", status_code=201)
def create(
    payload: AudienceGroupCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("audience:create")),
):
    data = _from_camel(payload.model_dump())
    obj = audience_groups.create_group(db, data)
    _audit(db, request, user, "create", obj)
    return ok(_serialize(obj, 0))


@router.get("/{group_id}")
def get_(
    group_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("audience:view")),
):
    obj = audience_groups.get_group(db, group_id)

    if not obj:
        raise NotFoundError("Group not found")

    return ok(_serialize(obj, audience_groups.member_count(db, obj.id)))


@router.patch("/{group_id}")
def update(
    group_id: str,
    payload: AudienceGroupUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("audience:edit")),
):
    obj = audience_groups.get_group(db, group_id)

    if not obj:
        raise NotFoundError("Group not found")

    data = _from_camel(payload.model_dump(exclude_none=True))
    audience_groups.update_group(db, obj, data)

    _audit(db, request, user, "update", obj)

    return ok(_serialize(obj, audience_groups.member_count(db, obj.id)))


@router.delete("/{group_id}")
def delete(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("audience:delete")),
):
    obj = audience_groups.get_group(db, group_id)

    if not obj:
        raise NotFoundError("Group not found")

    audience_groups.delete_group(db, obj)

    _audit(db, request, user, "delete", obj)

    return ok({"deleted": True})


@router.get("/{group_id}/members")
def list_members(
    group_id: str,
    pp: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("audience:view")),
):
    group = audience_groups.get_group(db, group_id)

    if not group:
        raise NotFoundError("Group not found")

    items, total = audience_groups.list_members(
        db,
        group_id,
        page=pp.page,
        page_size=pp.page_size,
        search=pp.search,
    )

    return paginated(
        [_serialize_member(member) for member in items],
        pp.page,
        pp.page_size,
        total,
    )


@router.post("/{group_id}/members")
def add_members(
    group_id: str,
    payload: AddMembersRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("audience:edit")),
):
    group = audience_groups.get_group(db, group_id)

    if not group:
        raise NotFoundError("Group not found")

    added, skipped = audience_groups.add_members(
        db,
        group_id,
        payload.audienceIds,
    )

    _audit(
        db,
        request,
        user,
        "add_members",
        group,
        {
            "added": added,
            "skipped": skipped,
        },
    )

    return ok(
        {
            "added": added,
            "skipped": skipped,
            "memberCount": audience_groups.member_count(db, group_id),
        }
    )


@router.delete("/{group_id}/members/{audience_id}")
def remove_member(
    group_id: str,
    audience_id: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_perm("audience:edit")),
):
    group = audience_groups.get_group(db, group_id)

    if not group:
        raise NotFoundError("Group not found")

    if not audience_groups.remove_member(db, group_id, audience_id):
        raise NotFoundError("Group member not found")

    _audit(
        db,
        request,
        user,
        "remove_member",
        group,
        {
            "audienceId": audience_id,
        },
    )

    return ok(
        {
            "removed": True,
            "memberCount": audience_groups.member_count(db, group_id),
        }
    )