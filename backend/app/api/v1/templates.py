from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.campaign import CampaignTemplate
from app.models.template import Template, TemplateVersion
from app.models.user import User
from app.repositories import templates
from app.schemas.template import TemplateCreate, TemplateUpdate
from app.services import audit

router = APIRouter()


def _serialize(t: Template) -> dict:
    return {
        "id": str(t.id),
        "workspaceId": str(t.workspace_id),
        "name": t.name,
        "category": t.category,
        "channels": t.channels or [],
        "language": t.language,
        "version": t.version,
        "status": t.status,
        "body": t.body,
        "createdAt": t.created_at.isoformat(),
        "updatedAt": t.updated_at.isoformat(),
        "deletedAt": t.deleted_at.isoformat() if t.deleted_at else None,
    }


def _audit(db, req, user, action, obj):
    audit.log(db, action=action, module="template", actor_id=user.id,
              workspace_id=obj.workspace_id, entity_id=str(obj.id),
              entity_label=obj.name, ip=req.client.host if req.client else None)


@router.get("")
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db),
          _: User = Depends(require_perm("template:view"))):
    items, total = templates.list(
        db, page=pp.page, page_size=pp.page_size, search=pp.search,
        search_fields=["name", "category"], sort_by=pp.sort_by, sort_dir=pp.sort_dir,
    )
    return paginated([_serialize(x) for x in items], pp.page, pp.page_size, total)


@router.post("", status_code=201)
def create(payload: TemplateCreate, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_perm("template:create"))):
    data = payload.model_dump(); data["workspace_id"] = data.pop("workspaceId")
    obj = templates.create(db, data)
    db.add(TemplateVersion(template_id=obj.id, version=1, body=obj.body, note="initial"))
    db.commit()
    _audit(db, request, user, "create", obj)
    return ok(_serialize(obj))


@router.get("/{tid}")
def get_(tid: str, db: Session = Depends(get_db),
         _: User = Depends(require_perm("template:view"))):
    obj = templates.get(db, tid)
    if not obj:
        raise NotFoundError("Template not found")
    return ok(_serialize(obj))


@router.patch("/{tid}")
def update(tid: str, payload: TemplateUpdate, request: Request,
           db: Session = Depends(get_db),
           user: User = Depends(require_perm("template:edit"))):
    obj = templates.get(db, tid)
    if not obj:
        raise NotFoundError("Template not found")
    data = payload.model_dump(exclude_none=True)
    body_changed = "body" in data and data["body"] != obj.body
    templates.update(db, obj, data)
    if body_changed:
        obj.version += 1
        db.add(TemplateVersion(template_id=obj.id, version=obj.version, body=obj.body,
                               note="updated"))
        db.commit(); db.refresh(obj)
    _audit(db, request, user, "update", obj)
    return ok(_serialize(obj))


@router.delete("/{tid}")
def delete(tid: str, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_perm("template:delete"))):
    obj = templates.get(db, tid)
    if not obj:
        raise NotFoundError("Template not found")
    templates.soft_delete(db, obj)
    _audit(db, request, user, "delete", obj)
    return ok({"deleted": True})


@router.post("/{tid}/restore")
def restore(tid: str, request: Request, db: Session = Depends(get_db),
            user: User = Depends(require_perm("template:edit"))):
    obj = db.get(Template, tid)
    if not obj:
        raise NotFoundError("Template not found")
    obj.deleted_at = None
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "restore", obj)
    return ok(_serialize(obj))


@router.post("/{tid}/clone", status_code=201)
def clone(tid: str, request: Request, db: Session = Depends(get_db),
          user: User = Depends(require_perm("template:create"))):
    src = templates.get(db, tid)
    if not src:
        raise NotFoundError("Template not found")
    dup = Template(
        workspace_id=src.workspace_id, name=f"{src.name} (copy)",
        category=src.category, channels=list(src.channels or []),
        language=src.language, version=1, status="draft", body=src.body,
    )
    db.add(dup); db.commit(); db.refresh(dup)
    db.add(TemplateVersion(template_id=dup.id, version=1, body=dup.body,
                           note=f"cloned from {src.id}"))
    db.commit()
    _audit(db, request, user, "clone", dup)
    return ok(_serialize(dup))


@router.get("/{tid}/versions")
def versions(tid: str, db: Session = Depends(get_db),
             _: User = Depends(require_perm("template:view"))):
    if not templates.get(db, tid):
        raise NotFoundError("Template not found")
    rows = db.scalars(select(TemplateVersion).where(TemplateVersion.template_id == tid)
                      .order_by(TemplateVersion.version.desc())).all()
    return ok({"items": [
        {"id": str(v.id), "version": v.version, "body": v.body, "note": v.note,
         "createdAt": v.created_at.isoformat()} for v in rows
    ]})


@router.post("/{tid}/versions/{version}/restore")
def restore_version(tid: str, version: int, request: Request,
                    db: Session = Depends(get_db),
                    user: User = Depends(require_perm("template:edit"))):
    obj = templates.get(db, tid)
    if not obj:
        raise NotFoundError("Template not found")
    ver = db.scalar(select(TemplateVersion).where(
        TemplateVersion.template_id == tid, TemplateVersion.version == version))
    if not ver:
        raise NotFoundError("Version not found")
    obj.body = ver.body
    obj.version += 1
    db.add(TemplateVersion(template_id=obj.id, version=obj.version, body=obj.body,
                           note=f"restored v{version}"))
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "restore_version", obj)
    return ok(_serialize(obj))


@router.get("/{tid}/usage")
def usage(tid: str, db: Session = Depends(get_db),
          _: User = Depends(require_perm("template:view"))):
    from sqlalchemy import func
    n = db.scalar(select(func.count(CampaignTemplate.campaign_id)).where(
        CampaignTemplate.template_id == tid)) or 0
    return ok({"campaignCount": int(n)})
