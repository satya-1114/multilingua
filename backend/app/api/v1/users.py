from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.responses import ok, paginated
from app.dependencies.auth import current_user, require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.user import User
from app.repositories import users
from app.schemas.user import UserUpdate
from app.services import audit

router = APIRouter()


def _serialize(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "fullName": u.full_name,
        "avatarUrl": u.avatar_url,
        "status": "active" if u.is_active else "suspended",
        "roles": [r.name for r in u.roles],
        "defaultWorkspaceId": str(u.default_workspace_id) if u.default_workspace_id else None,
        "createdAt": u.created_at.isoformat(),
        "updatedAt": u.updated_at.isoformat(),
        "deletedAt": u.deleted_at.isoformat() if u.deleted_at else None,
    }


def _audit(db, req, user, action, obj):
    audit.log(db, action=action, module="user", actor_id=user.id,
              entity_id=str(obj.id), entity_label=obj.email,
              ip=req.client.host if req.client else None)


@router.get("/me")
def me(user: User = Depends(current_user)):
    return ok(_serialize(user))


@router.get("")
def list_users(pp: PageParams = Depends(page_params), db: Session = Depends(get_db),
               _: User = Depends(require_perm("user:view"))):
    items, total = users.list(
        db, page=pp.page, page_size=pp.page_size, search=pp.search,
        search_fields=["email", "full_name"], sort_by=pp.sort_by, sort_dir=pp.sort_dir,
    )
    return paginated([_serialize(u) for u in items], pp.page, pp.page_size, total)


@router.get("/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db),
             _: User = Depends(require_perm("user:view"))):
    obj = users.get(db, user_id)
    if not obj:
        raise NotFoundError("User not found")
    return ok(_serialize(obj))


@router.patch("/{user_id}")
def update_user(user_id: str, payload: UserUpdate, request: Request,
                db: Session = Depends(get_db),
                user: User = Depends(require_perm("user:manage"))):
    obj = users.get(db, user_id)
    if not obj:
        raise NotFoundError("User not found")
    data = payload.model_dump(exclude_none=True, by_alias=False)
    if "fullName" in data:
        data["full_name"] = data.pop("fullName")
    if "avatarUrl" in data:
        data["avatar_url"] = data.pop("avatarUrl")
    data.pop("roles", None)
    users.update(db, obj, data)
    _audit(db, request, user, "update", obj)
    return ok(_serialize(obj))


@router.delete("/{user_id}")
def delete_user(user_id: str, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_perm("user:manage"))):
    obj = users.get(db, user_id)
    if not obj:
        raise NotFoundError("User not found")
    users.soft_delete(db, obj)
    _audit(db, request, user, "delete", obj)
    return ok({"deleted": True})


@router.post("/{user_id}/restore")
def restore(user_id: str, request: Request, db: Session = Depends(get_db),
            user: User = Depends(require_perm("user:manage"))):
    obj = db.get(User, user_id)
    if not obj:
        raise NotFoundError("User not found")
    obj.deleted_at = None
    obj.is_active = True
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "restore", obj)
    return ok(_serialize(obj))


class BulkIds(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)


@router.post("/bulk-delete")
def bulk_delete(payload: BulkIds, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_perm("user:manage"))):
    n = 0
    for i in payload.ids:
        if str(user.id) == i:  # never self-delete
            continue
        obj = users.get(db, i)
        if obj:
            users.soft_delete(db, obj); n += 1
    audit.log(db, action="bulk_delete", module="user", actor_id=user.id,
              metadata={"count": n}, ip=request.client.host if request.client else None)
    return ok({"deleted": n})
