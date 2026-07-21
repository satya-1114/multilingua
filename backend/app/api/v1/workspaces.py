from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.responses import ok, paginated
from app.dependencies.auth import current_user, require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories import workspaces
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from app.services import audit

router = APIRouter()


def _serialize(w: Workspace) -> dict:
    return {
        "id": str(w.id),
        "organizationId": str(w.organization_id),
        "name": w.name, "slug": w.slug, "plan": w.plan,
        "region": w.region, "timezone": w.timezone,
        "primaryLanguage": w.primary_language,
        "storageQuotaGb": w.storage_quota_gb,
        "apiQuotaMonthly": w.api_quota_monthly,
        "memberCount": w.member_count,
        "createdAt": w.created_at.isoformat(),
        "updatedAt": w.updated_at.isoformat(),
    }


def _audit(db, req, user, action, obj):
    audit.log(db, action=action, module="workspace", actor_id=user.id,
              workspace_id=obj.id, entity_id=str(obj.id), entity_label=obj.name,
              ip=req.client.host if req.client else None)


@router.get("")
def list_ws(pp: PageParams = Depends(page_params), db: Session = Depends(get_db),
            _: User = Depends(require_perm("workspace:view"))):
    items, total = workspaces.list(
        db, page=pp.page, page_size=pp.page_size, search=pp.search,
        search_fields=["name", "slug"], sort_by=pp.sort_by, sort_dir=pp.sort_dir,
    )
    return paginated([_serialize(w) for w in items], pp.page, pp.page_size, total)


@router.post("", status_code=201)
def create_ws(payload: WorkspaceCreate, request: Request, db: Session = Depends(get_db),
              user: User = Depends(require_perm("workspace:manage"))):
    data = payload.model_dump()
    data["organization_id"] = data.pop("organizationId")
    data["primary_language"] = data.pop("primaryLanguage")
    exists = db.scalar(select(Workspace).where(Workspace.slug == data["slug"]))
    if exists:
        raise ValidationError("Slug already in use")
    obj = workspaces.create(db, data)
    _audit(db, request, user, "create", obj)
    return ok(_serialize(obj))


@router.get("/{ws_id}")
def get_ws(ws_id: str, db: Session = Depends(get_db),
           _: User = Depends(require_perm("workspace:view"))):
    obj = workspaces.get(db, ws_id)
    if not obj:
        raise NotFoundError("Workspace not found")
    return ok(_serialize(obj))


@router.patch("/{ws_id}")
def update_ws(ws_id: str, payload: WorkspaceUpdate, request: Request,
              db: Session = Depends(get_db),
              user: User = Depends(require_perm("workspace:manage"))):
    obj = workspaces.get(db, ws_id)
    if not obj:
        raise NotFoundError("Workspace not found")
    data = payload.model_dump(exclude_none=True)
    if "primaryLanguage" in data:
        data["primary_language"] = data.pop("primaryLanguage")
    workspaces.update(db, obj, data)
    _audit(db, request, user, "update", obj)
    return ok(_serialize(obj))


@router.delete("/{ws_id}")
def delete_ws(ws_id: str, request: Request, db: Session = Depends(get_db),
              user: User = Depends(require_perm("workspace:manage"))):
    obj = workspaces.get(db, ws_id)
    if not obj:
        raise NotFoundError("Workspace not found")
    workspaces.soft_delete(db, obj)
    _audit(db, request, user, "delete", obj)
    return ok({"deleted": True})


@router.get("/{ws_id}/members")
def list_members(ws_id: str, db: Session = Depends(get_db),
                 _: User = Depends(require_perm("workspace:view"))):
    rows = db.scalars(select(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_id)).all()
    users_map = {}
    if rows:
        users_map = {str(u.id): u for u in db.scalars(
            select(User).where(User.id.in_([r.user_id for r in rows]))).all()}
    return ok({"items": [
        {
            "userId": str(r.user_id), "role": r.role,
            "email": users_map[str(r.user_id)].email if str(r.user_id) in users_map else None,
            "fullName": users_map[str(r.user_id)].full_name if str(r.user_id) in users_map else None,
        } for r in rows
    ]})


class MemberPayload(BaseModel):
    userId: str
    role: str = "viewer"


@router.post("/{ws_id}/members", status_code=201)
def add_member(ws_id: str, payload: MemberPayload, request: Request,
               db: Session = Depends(get_db),
               user: User = Depends(require_perm("workspace:manage"))):
    ws = workspaces.get(db, ws_id) or (_ for _ in ()).throw(NotFoundError("Workspace not found"))
    existing = db.scalar(select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == ws_id, WorkspaceMember.user_id == payload.userId))
    if existing:
        existing.role = payload.role
    else:
        db.add(WorkspaceMember(workspace_id=ws_id, user_id=payload.userId, role=payload.role))
        ws.member_count = (ws.member_count or 0) + 1
    db.commit()
    _audit(db, request, user, "add_member", ws)
    return ok({"userId": payload.userId, "role": payload.role})


@router.delete("/{ws_id}/members/{uid}")
def remove_member(ws_id: str, uid: str, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_perm("workspace:manage"))):
    ws = workspaces.get(db, ws_id) or (_ for _ in ()).throw(NotFoundError("Workspace not found"))
    row = db.scalar(select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == ws_id, WorkspaceMember.user_id == uid))
    if not row:
        raise NotFoundError("Member not found")
    db.delete(row)
    ws.member_count = max(0, (ws.member_count or 0) - 1)
    db.commit()
    _audit(db, request, user, "remove_member", ws)
    return ok({"removed": True})


class InvitePayload(BaseModel):
    email: EmailStr
    role: str = "viewer"


@router.post("/{ws_id}/invitations", status_code=201)
def invite(ws_id: str, payload: InvitePayload, request: Request,
           db: Session = Depends(get_db),
           user: User = Depends(require_perm("workspace:manage"))):
    ws = workspaces.get(db, ws_id) or (_ for _ in ()).throw(NotFoundError("Workspace not found"))
    audit.log(db, action="invite", module="workspace", actor_id=user.id,
              workspace_id=ws.id, entity_label=payload.email,
              metadata={"role": payload.role},
              ip=request.client.host if request.client else None)
    # Real send handled by communication service in later slice
    return ok({"invited": payload.email, "role": payload.role, "workspaceId": ws_id})


@router.post("/{ws_id}/switch")
def switch(ws_id: str, db: Session = Depends(get_db),
           user: User = Depends(current_user)):
    ws = workspaces.get(db, ws_id)
    if not ws:
        raise NotFoundError("Workspace not found")
    user.default_workspace_id = ws.id
    db.commit()
    return ok({"workspaceId": str(ws.id)})
