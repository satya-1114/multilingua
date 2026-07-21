from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.audience import Audience
from app.models.user import User
from app.repositories import audience
from app.schemas.audience import AudienceCreate, AudienceUpdate
from app.services import audit

router = APIRouter()


def _serialize(a: Audience) -> dict:
    return {
        "id": str(a.id),
        "workspaceId": str(a.workspace_id),
        "fullName": a.full_name,
        "email": a.email,
        "phone": a.phone,
        "language": a.language,
        "tags": a.tags or [],
        "status": a.status,
        "district": a.district,
        "state": a.state,
        "createdAt": a.created_at.isoformat(),
        "updatedAt": a.updated_at.isoformat(),
        "deletedAt": a.deleted_at.isoformat() if a.deleted_at else None,
    }


def _from_camel(data: dict) -> dict:
    if "fullName" in data:
        data["full_name"] = data.pop("fullName")
    if "workspaceId" in data:
        data["workspace_id"] = data.pop("workspaceId")
    return data


def _audit(db, req, user, action, obj):
    audit.log(
        db, action=action, module="audience", actor_id=user.id,
        workspace_id=getattr(obj, "workspace_id", None),
        entity_id=str(getattr(obj, "id", "")), entity_label=getattr(obj, "full_name", None),
        ip=req.client.host if req.client else None, ua=req.headers.get("user-agent"),
    )


@router.get("")
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db),
          _: User = Depends(require_perm("audience:view"))):
    items, total = audience.list(
        db, page=pp.page, page_size=pp.page_size, search=pp.search,
        search_fields=["full_name", "email", "phone"],
        sort_by=pp.sort_by, sort_dir=pp.sort_dir,
    )
    return paginated([_serialize(x) for x in items], pp.page, pp.page_size, total)


@router.post("", status_code=201)
def create(payload: AudienceCreate, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_perm("audience:create"))):
    data = _from_camel(payload.model_dump())
    # duplicate detection by email within workspace
    if data.get("email"):
        exists = db.scalar(select(Audience).where(
            Audience.workspace_id == data["workspace_id"],
            Audience.email == data["email"],
            Audience.deleted_at.is_(None),
        ))
        if exists:
            raise ValidationError("A contact with this email already exists")
    obj = audience.create(db, data)
    _audit(db, request, user, "create", obj)
    return ok(_serialize(obj))


@router.get("/duplicates")
def duplicates(workspaceId: str, db: Session = Depends(get_db),
               _: User = Depends(require_perm("audience:view"))):
    stmt = (
        select(Audience.email, func.count(Audience.id).label("n"))
        .where(Audience.workspace_id == workspaceId, Audience.email.is_not(None),
               Audience.deleted_at.is_(None))
        .group_by(Audience.email).having(func.count(Audience.id) > 1)
    )
    rows = [{"email": r[0], "count": int(r[1])} for r in db.execute(stmt).all()]
    return ok({"items": rows, "total": len(rows)})


@router.get("/export")
def export_csv(workspaceId: str, db: Session = Depends(get_db),
               _: User = Depends(require_perm("audience:view"))):
    stmt = select(Audience).where(
        Audience.workspace_id == workspaceId, Audience.deleted_at.is_(None)
    )
    rows = list(db.scalars(stmt))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["full_name", "email", "phone", "language", "status", "tags", "district", "state"])
    for r in rows:
        w.writerow([r.full_name, r.email or "", r.phone or "", r.language, r.status,
                    ",".join(r.tags or []), r.district or "", r.state or ""])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audience-{workspaceId}.csv"},
    )


@router.post("/import")
async def import_csv(workspaceId: str, request: Request, file: UploadFile = File(...),
                     db: Session = Depends(get_db),
                     user: User = Depends(require_perm("audience:create"))):
    content = (await file.read()).decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    created = 0
    skipped = 0
    errors: list[dict] = []
    seen: set[str] = set()
    for idx, row in enumerate(reader, start=2):
        name = (row.get("full_name") or row.get("fullName") or "").strip()
        if not name:
            errors.append({"row": idx, "error": "missing full_name"})
            continue
        email = (row.get("email") or "").strip() or None
        key = (email or "").lower()
        if email and key in seen:
            skipped += 1
            continue
        if email:
            existing = db.scalar(select(Audience).where(
                Audience.workspace_id == workspaceId, Audience.email == email,
                Audience.deleted_at.is_(None),
            ))
            if existing:
                skipped += 1
                continue
            seen.add(key)
        tags_raw = (row.get("tags") or "").strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
        obj = Audience(
            workspace_id=workspaceId,
            full_name=name, email=email,
            phone=(row.get("phone") or "").strip() or None,
            language=(row.get("language") or "en").strip() or "en",
            status=(row.get("status") or "active").strip() or "active",
            tags=tags,
            district=(row.get("district") or "").strip() or None,
            state=(row.get("state") or "").strip() or None,
        )
        db.add(obj)
        created += 1
    db.commit()
    audit.log(db, action="import", module="audience", actor_id=user.id,
              workspace_id=workspaceId, entity_label=file.filename,
              ip=request.client.host if request.client else None,
              metadata={"created": created, "skipped": skipped, "errors": len(errors)})
    return ok({"created": created, "skipped": skipped, "errors": errors})


@router.post("/import/preview")
async def import_preview(file: UploadFile = File(...),
                         _: User = Depends(require_perm("audience:create"))):
    from app.services import csv_import
    data = await file.read()
    return ok(csv_import.audience_preview(data))


class BulkIds(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=1000)


class BulkUpdate(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=1000)
    status: str | None = None
    language: str | None = None
    addTags: list[str] | None = None
    removeTags: list[str] | None = None


@router.post("/bulk-delete")
def bulk_delete(payload: BulkIds, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_perm("audience:delete"))):
    n = 0
    for i in payload.ids:
        obj = audience.get(db, i)
        if obj:
            audience.soft_delete(db, obj)
            n += 1
    audit.log(db, action="bulk_delete", module="audience", actor_id=user.id,
              metadata={"count": n}, ip=request.client.host if request.client else None)
    return ok({"deleted": n})


@router.post("/bulk-update")
def bulk_update(payload: BulkUpdate, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_perm("audience:edit"))):
    n = 0
    for i in payload.ids:
        obj = audience.get(db, i)
        if not obj:
            continue
        if payload.status is not None:
            obj.status = payload.status
        if payload.language is not None:
            obj.language = payload.language
        current = set(obj.tags or [])
        if payload.addTags:
            current.update(payload.addTags)
        if payload.removeTags:
            current.difference_update(payload.removeTags)
        obj.tags = sorted(current)
        n += 1
    db.commit()
    audit.log(db, action="bulk_update", module="audience", actor_id=user.id,
              metadata={"count": n}, ip=request.client.host if request.client else None)
    return ok({"updated": n})


@router.get("/{item_id}")
def get_(item_id: str, db: Session = Depends(get_db),
         _: User = Depends(require_perm("audience:view"))):
    obj = audience.get(db, item_id)
    if not obj:
        raise NotFoundError("Contact not found")
    return ok(_serialize(obj))


@router.patch("/{item_id}")
def update(item_id: str, payload: AudienceUpdate, request: Request,
           db: Session = Depends(get_db),
           user: User = Depends(require_perm("audience:edit"))):
    obj = audience.get(db, item_id)
    if not obj:
        raise NotFoundError("Contact not found")
    data = _from_camel(payload.model_dump(exclude_none=True))
    audience.update(db, obj, data)
    _audit(db, request, user, "update", obj)
    return ok(_serialize(obj))


@router.delete("/{item_id}")
def delete(item_id: str, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_perm("audience:delete"))):
    obj = audience.get(db, item_id)
    if not obj:
        raise NotFoundError("Contact not found")
    audience.soft_delete(db, obj)
    _audit(db, request, user, "delete", obj)
    return ok({"deleted": True})


@router.post("/{item_id}/restore")
def restore(item_id: str, request: Request, db: Session = Depends(get_db),
            user: User = Depends(require_perm("audience:edit"))):
    obj = db.get(Audience, item_id)
    if not obj:
        raise NotFoundError("Contact not found")
    obj.deleted_at = None
    db.commit()
    db.refresh(obj)
    _audit(db, request, user, "restore", obj)
    return ok(_serialize(obj))
