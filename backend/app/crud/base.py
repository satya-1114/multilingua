from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database.base import Base

M = TypeVar("M", bound=Base)


class CRUDBase(Generic[M]):
    def __init__(self, model: type[M]) -> None:
        self.model = model

    def get(self, db: Session, id: Any) -> M | None:
        obj = db.get(self.model, id)
        if obj and getattr(obj, "deleted_at", None) is not None:
            return None
        return obj

    def list(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
        search_fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[M], int]:
        stmt = select(self.model)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        for k, v in (filters or {}).items():
            if v is None or not hasattr(self.model, k):
                continue
            stmt = stmt.where(getattr(self.model, k) == v)
        if search and search_fields:
            like = f"%{search}%"
            stmt = stmt.where(or_(*[getattr(self.model, f).ilike(like) for f in search_fields if hasattr(self.model, f)]))
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(self.model, sort_by):
            col = getattr(self.model, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        elif hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = list(db.scalars(stmt))
        return items, int(total)

    def create(self, db: Session, data: dict[str, Any]) -> M:
        obj = self.model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, obj: M, data: dict[str, Any]) -> M:
        for k, v in data.items():
            if v is not None and hasattr(obj, k):
                setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return obj

    def soft_delete(self, db: Session, obj: M) -> None:
        from datetime import datetime, timezone
        if hasattr(obj, "deleted_at"):
            setattr(obj, "deleted_at", datetime.now(timezone.utc))
            db.commit()
        else:
            db.delete(obj)
            db.commit()
