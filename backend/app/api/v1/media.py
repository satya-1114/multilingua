from __future__ import annotations

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError, NotFoundError
from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.media import Media
from app.models.user import User
from app.repositories import media as media_repo
from app.services import storage, upload

router = APIRouter()


def _serialize(m: Media) -> dict:
    return {
        "id": str(m.id), "name": m.name, "mimeType": m.mime_type, "sizeBytes": m.size_bytes,
        "url": m.url, "checksum": m.checksum,
        "createdAt": m.created_at.isoformat(), "updatedAt": m.updated_at.isoformat(),
    }


@router.get("")
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db), _: User = Depends(require_perm("media:view"))):
    items, total = media_repo.list(
        db, page=pp.page, page_size=pp.page_size, search=pp.search,
        search_fields=["name"], sort_by=pp.sort_by, sort_dir=pp.sort_dir,
    )
    return paginated([_serialize(x) for x in items], pp.page, pp.page_size, total)


@router.post("", status_code=201)
async def upload_single(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    optimize: bool = Form(False),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("media:upload")),
):
    data = await file.read()
    storage.validate(name=file.filename or "upload", mime=file.content_type or "application/octet-stream", size=len(data))
    if optimize and (file.content_type or "").startswith("image/"):
        data = upload.optimize_image(data)
    path, checksum = storage.save_local(name=file.filename or "upload", data=data)
    metadata = upload.extract_metadata(mime=file.content_type or "", data=data)
    obj = media_repo.create(
        db,
        {
            "workspace_id": workspace_id,
            "name": file.filename or "upload",
            "mime_type": file.content_type or "application/octet-stream",
            "size_bytes": len(data),
            "url": upload.signed_url(path),
            "checksum": checksum,
        },
    )
    payload = _serialize(obj)
    payload["metadata"] = metadata
    return ok(payload)


class ChunkInit(BaseModel):
    workspaceId: str
    name: str
    mimeType: str
    totalSize: int
    chunkSize: int = 5 * 1024 * 1024
    checksum: str | None = None


@router.post("/chunks/init", status_code=201)
def chunk_init(payload: ChunkInit, _: User = Depends(require_perm("media:upload"))):
    try:
        session = upload.start_session(
            name=payload.name, mime=payload.mimeType, total_size=payload.totalSize,
            chunk_size=payload.chunkSize, checksum=payload.checksum,
        )
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ok({"sessionId": session.id, "chunkSize": session.chunk_size})


@router.post("/chunks/{sid}")
async def chunk_append(sid: str, index: int = Form(...), file: UploadFile = File(...),
                       _: User = Depends(require_perm("media:upload"))):
    data = await file.read()
    try:
        session = upload.append_chunk(sid, index=index, data=data)
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ok({"sessionId": session.id, "received": session.chunks_received, "bytes": len(session.buffer)})


@router.post("/chunks/{sid}/complete")
def chunk_complete(
    sid: str,
    workspace_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    _: User = Depends(require_perm("media:upload")),
):
    try:
        result = upload.finalize(sid)
    except DomainError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    obj = media_repo.create(
        db,
        {
            "workspace_id": workspace_id,
            "name": result["name"],
            "mime_type": result["mime"],
            "size_bytes": result["size"],
            "url": result["url"],
            "checksum": result["checksum"],
        },
    )
    payload = _serialize(obj)
    payload["metadata"] = result["metadata"]
    return ok(payload)


@router.get("/{mid}/signed-url")
def signed(mid: str, expires_in: int = 3600, db: Session = Depends(get_db), _: User = Depends(require_perm("media:view"))):
    obj = media_repo.get(db, mid)
    if not obj:
        raise NotFoundError("Media not found")
    return ok({"url": upload.signed_url(obj.url, expires_in=expires_in), "expiresIn": expires_in})


@router.delete("/{mid}")
def delete(mid: str, db: Session = Depends(get_db), _: User = Depends(require_perm("media:delete"))):
    obj = media_repo.get(db, mid)
    if not obj:
        raise NotFoundError("Media not found")
    media_repo.soft_delete(db, obj)
    return ok({"deleted": True})
