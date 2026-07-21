from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.organization import Organization
from app.models.user import User
from app.repositories import organizations
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services import audit

router = APIRouter()


def _serialize(o: Organization) -> dict:
    return {
        "id": str(o.id), "name": o.name, "slug": o.slug, "type": o.type,
        "status": o.status, "website": o.website, "contactEmail": o.contact_email,
        "memberCount": o.member_count, "region": o.region,
        "createdAt": o.created_at.isoformat(), "updatedAt": o.updated_at.isoformat(),
        "deletedAt": o.deleted_at.isoformat() if o.deleted_at else None,
    }


def _from_camel(d: dict) -> dict:
    if "contactEmail" in d:
        d["contact_email"] = d.pop("contactEmail")
    return d


def _audit(db, req, user, action, obj):
    audit.log(db, action=action, module="organization", actor_id=user.id,
              entity_id=str(obj.id), entity_label=obj.name,
              ip=req.client.host if req.client else None)


@router.get("")
def list_orgs(pp: PageParams = Depends(page_params), db: Session = Depends(get_db),
              _: User = Depends(require_perm("org:view"))):
    items, total = organizations.list(
        db, page=pp.page, page_size=pp.page_size, search=pp.search,
        search_fields=["name", "slug"], sort_by=pp.sort_by, sort_dir=pp.sort_dir,
    )
    return paginated([_serialize(x) for x in items], pp.page, pp.page_size, total)


@router.post("", status_code=201)
def create_org(payload: OrganizationCreate, request: Request,
               db: Session = Depends(get_db),
               user: User = Depends(require_perm("org:create"))):
    data = _from_camel(payload.model_dump())
    if db.scalar(select(Organization).where(Organization.slug == data["slug"])):
        raise ValidationError("Slug already in use")
    obj = organizations.create(db, data)
    _audit(db, request, user, "create", obj)
    return ok(_serialize(obj))


@router.get("/{org_id}")
def get_org(org_id: str, db: Session = Depends(get_db),
            _: User = Depends(require_perm("org:view"))):
    obj = organizations.get(db, org_id)
    if not obj:
        raise NotFoundError("Organization not found")
    return ok(_serialize(obj))


@router.patch("/{org_id}")
def update_org(org_id: str, payload: OrganizationUpdate, request: Request,
               db: Session = Depends(get_db),
               user: User = Depends(require_perm("org:edit"))):
    obj = organizations.get(db, org_id)
    if not obj:
        raise NotFoundError("Organization not found")
    organizations.update(db, obj, _from_camel(payload.model_dump(exclude_none=True)))
    _audit(db, request, user, "update", obj)
    return ok(_serialize(obj))


@router.delete("/{org_id}")
def delete_org(org_id: str, request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_perm("org:delete"))):
    obj = organizations.get(db, org_id)
    if not obj:
        raise NotFoundError("Organization not found")
    organizations.soft_delete(db, obj)
    _audit(db, request, user, "delete", obj)
    return ok({"deleted": True})


@router.post("/{org_id}/restore")
def restore(org_id: str, request: Request, db: Session = Depends(get_db),
            user: User = Depends(require_perm("org:edit"))):
    obj = db.get(Organization, org_id)
    if not obj:
        raise NotFoundError("Organization not found")
    obj.deleted_at = None
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "restore", obj)
    return ok(_serialize(obj))
