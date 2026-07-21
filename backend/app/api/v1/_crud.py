"""Reusable helpers for building CRUD routers."""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.responses import ok, paginated
from app.crud.base import CRUDBase
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params


def crud_list(
    repo: CRUDBase,
    serializer: Callable[[Any], dict],
    *,
    search_fields: list[str] | None = None,
):
    def endpoint(pp: PageParams = Depends(page_params), db: Session = Depends(get_db)):
        items, total = repo.list(
            db,
            page=pp.page,
            page_size=pp.page_size,
            search=pp.search,
            search_fields=search_fields,
            sort_by=pp.sort_by,
            sort_dir=pp.sort_dir,
        )
        return paginated([serializer(i) for i in items], pp.page, pp.page_size, total)
    return endpoint


def crud_get(repo: CRUDBase, serializer: Callable[[Any], dict]):
    def endpoint(item_id: str, db: Session = Depends(get_db)):
        obj = repo.get(db, item_id)
        if not obj:
            raise NotFoundError("Resource not found")
        return ok(serializer(obj))
    return endpoint


def crud_delete(repo: CRUDBase):
    def endpoint(item_id: str, db: Session = Depends(get_db)):
        obj = repo.get(db, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Not found")
        repo.soft_delete(db, obj)
        return ok({"deleted": True})
    return endpoint
