from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.analytics import Report
from app.models.user import User
from app.services import reports as reports_service

router = APIRouter()


class ReportIn(BaseModel):
    workspaceId: str
    name: str
    kind: str
    scheduled: bool = False
    filters: dict[str, Any] = {}


def _serialize(r: Report) -> dict:
    return {
        "id": str(r.id), "name": r.name, "kind": r.kind, "scheduled": r.scheduled,
        "filters": r.filters or {},
        "lastRunAt": r.last_run_at.isoformat() if r.last_run_at else None,
        "createdAt": r.created_at.isoformat(), "updatedAt": r.updated_at.isoformat(),
    }


@router.get("")
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:view"))):
    total = db.query(Report).count()
    rows = db.query(Report).offset((pp.page - 1) * pp.page_size).limit(pp.page_size).all()
    return paginated([_serialize(r) for r in rows], pp.page, pp.page_size, total)


@router.get("/kinds")
def kinds(_: User = Depends(require_perm("analytics:view"))):
    return ok(sorted(reports_service.REPORT_KINDS))


@router.post("", status_code=201)
def create(payload: ReportIn, db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:manage"))):
    try:
        r = reports_service.create_report(
            db, workspace_id=payload.workspaceId, name=payload.name,
            kind=payload.kind, scheduled=payload.scheduled, filters=payload.filters,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ok(_serialize(r))


@router.get("/{rid}")
def get(rid: str, db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:view"))):
    r = db.get(Report, rid)
    if not r:
        raise NotFoundError("Report not found")
    return ok(_serialize(r))


@router.post("/{rid}/run")
def run(
    rid: str,
    format: str = Query("json", pattern="^(json|csv|excel|xlsx|pdf)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    r = db.get(Report, rid)
    if not r:
        raise NotFoundError("Report not found")
    payload, mime, filename = reports_service.run_report(db, r, format=format)
    return _download(payload, mime, filename)


@router.post("/ad-hoc")
def ad_hoc(
    kind: str,
    format: str = Query("json", pattern="^(json|csv|excel|xlsx|pdf)$"),
    workspace_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("analytics:view")),
):
    try:
        payload, mime, filename = reports_service.run_ad_hoc(
            db, kind=kind, filters={"workspaceId": workspace_id}, format=format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _download(payload, mime, filename)


@router.delete("/{rid}")
def delete(rid: str, db: Session = Depends(get_db), _: User = Depends(require_perm("analytics:manage"))):
    r = db.get(Report, rid)
    if not r:
        raise NotFoundError("Report not found")
    db.delete(r)
    db.commit()
    return ok({"deleted": True})


def _download(payload: bytes, mime: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([payload]),
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
