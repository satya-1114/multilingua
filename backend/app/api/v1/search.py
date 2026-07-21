from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.dependencies.rbac import resolve_permissions
from app.models.user import User
from app.services import search as search_service

router = APIRouter()


@router.get("")
def global_search(
    q: str = Query(..., min_length=1, max_length=200),
    workspace_id: str | None = Query(None),
    scopes: str | None = Query(None, description="Comma-separated list of scopes"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    perms = set(resolve_permissions(user))
    scope_list = [s.strip() for s in scopes.split(",")] if scopes else None
    return ok(search_service.search(
        db, q=q, permissions=perms, scopes=scope_list,
        workspace_id=workspace_id, user_id=str(user.id), limit_total=limit,
    ))


@router.get("/suggest")
def suggest(q: str = Query("", max_length=100), db: Session = Depends(get_db), _: User = Depends(current_user)):
    return ok(search_service.suggestions(db, q))
