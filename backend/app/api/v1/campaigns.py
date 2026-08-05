from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.campaign import Approval, Campaign
from app.models.user import User
from app.repositories import campaigns
from app.repositories import campaign_assignments as campaign_assign_repo
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.schemas.campaign_assignment import CampaignAudienceRequest, CampaignTemplateRequest
from app.services import audit

router = APIRouter()

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_approval", "archived"},
    "pending_approval": {"approved", "rejected", "draft"},
    "approved": {"scheduled", "published", "archived"},
    "rejected": {"draft", "archived"},
    "scheduled": {"published", "draft", "archived"},
    "published": {"archived"},
    "archived": {"draft"},
}


def _serialize(c: Campaign) -> dict:
    return {
        "id": str(c.id),
        "workspaceId": str(c.workspace_id),
        "name": c.name,
        "status": c.status,
        "channels": c.channels or [],
        "audienceCount": c.audience_count,
        "startsAt": c.starts_at.isoformat() if c.starts_at else None,
        "endsAt": c.ends_at.isoformat() if c.ends_at else None,
        "createdAt": c.created_at.isoformat(),
        "updatedAt": c.updated_at.isoformat(),
        "deletedAt": c.deleted_at.isoformat() if c.deleted_at else None,
    }


def _from_camel(d: dict) -> dict:
    for a, b in [("workspaceId", "workspace_id"), ("startsAt", "starts_at"), ("endsAt", "ends_at")]:
        if a in d:
            d[b] = d.pop(a)
    return d


def _transition(obj: Campaign, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(obj.status, set())
    if target not in allowed:
        raise ValidationError(f"Cannot transition from '{obj.status}' to '{target}'")
    obj.status = target


def _audit(db, req, user, action, obj):
    audit.log(db, action=action, module="campaign", actor_id=user.id,
              workspace_id=obj.workspace_id, entity_id=str(obj.id),
              entity_label=obj.name, ip=req.client.host if req.client else None,
              ua=req.headers.get("user-agent"))


@router.get("")
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db),
          _: User = Depends(require_perm("campaign:view"))):
    items, total = campaigns.list(
        db, page=pp.page, page_size=pp.page_size, search=pp.search,
        search_fields=["name"], sort_by=pp.sort_by, sort_dir=pp.sort_dir,
    )
    return paginated([_serialize(x) for x in items], pp.page, pp.page_size, total)


@router.post("", status_code=201)
def create(payload: CampaignCreate, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_perm("campaign:create"))):
    data = _from_camel(payload.model_dump())
    data["owner_id"] = user.id
    obj = campaigns.create(db, data)
    _audit(db, request, user, "create", obj)
    return ok(_serialize(obj))


@router.get("/{cid}")
def get_(cid: str, db: Session = Depends(get_db),
         _: User = Depends(require_perm("campaign:view"))):
    obj = campaigns.get(db, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    return ok(_serialize(obj))


@router.patch("/{cid}")
def update(cid: str, payload: CampaignUpdate, request: Request,
           db: Session = Depends(get_db),
           user: User = Depends(require_perm("campaign:edit"))):
    obj = campaigns.get(db, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    data = _from_camel(payload.model_dump(exclude_none=True))
    if "status" in data and data["status"] != obj.status:
        _transition(obj, data.pop("status"))
    campaigns.update(db, obj, data)
    _audit(db, request, user, "update", obj)
    return ok(_serialize(obj))


@router.delete("/{cid}")
def delete(cid: str, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_perm("campaign:delete"))):
    obj = campaigns.get(db, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    campaigns.soft_delete(db, obj)
    _audit(db, request, user, "delete", obj)
    return ok({"deleted": True})


@router.post("/{cid}/restore")
def restore(cid: str, request: Request, db: Session = Depends(get_db),
            user: User = Depends(require_perm("campaign:edit"))):
    obj = db.get(Campaign, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    obj.deleted_at = None
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "restore", obj)
    return ok(_serialize(obj))


class ApprovalPayload(BaseModel):
    note: str | None = None


@router.post("/{cid}/submit")
def submit(cid: str, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_perm("campaign:edit"))):
    obj = campaigns.get(db, cid) or (_ for _ in ()).throw(NotFoundError("Campaign not found"))
    _transition(obj, "pending_approval")
    db.add(Approval(campaign_id=obj.id, status="pending", reviewer_id=None))
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "submit", obj)
    return ok(_serialize(obj))


@router.post("/{cid}/approve")
def approve(cid: str, payload: ApprovalPayload, request: Request,
            db: Session = Depends(get_db),
            user: User = Depends(require_perm("campaign:approve"))):
    obj = campaigns.get(db, cid) or (_ for _ in ()).throw(NotFoundError("Campaign not found"))
    _transition(obj, "approved")
    db.add(Approval(campaign_id=obj.id, status="approved",
                    reviewer_id=user.id, note=payload.note))
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "approve", obj)
    return ok(_serialize(obj))


@router.post("/{cid}/reject")
def reject(cid: str, payload: ApprovalPayload, request: Request,
           db: Session = Depends(get_db),
           user: User = Depends(require_perm("campaign:approve"))):
    obj = campaigns.get(db, cid) or (_ for _ in ()).throw(NotFoundError("Campaign not found"))
    _transition(obj, "rejected")
    db.add(Approval(campaign_id=obj.id, status="rejected",
                    reviewer_id=user.id, note=payload.note))
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "reject", obj)
    return ok(_serialize(obj))


class SchedulePayload(BaseModel):
    startsAt: datetime
    endsAt: datetime | None = None


@router.post("/{cid}/schedule")
def schedule(cid: str, payload: SchedulePayload, request: Request,
             db: Session = Depends(get_db),
             user: User = Depends(require_perm("campaign:launch"))):
    obj = campaigns.get(db, cid) or (_ for _ in ()).throw(NotFoundError("Campaign not found"))
    if payload.endsAt and payload.endsAt <= payload.startsAt:
        raise ValidationError("endsAt must be after startsAt")
    _transition(obj, "scheduled")
    obj.starts_at = payload.startsAt
    obj.ends_at = payload.endsAt
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "schedule", obj)
    return ok(_serialize(obj))


@router.post("/{cid}/publish")
def publish(cid: str, request: Request, db: Session = Depends(get_db),
            user: User = Depends(require_perm("campaign:launch"))):
    from app.services.campaign_execution import publish as publish_campaign

    obj = campaigns.get(db, cid) or (_ for _ in ()).throw(NotFoundError("Campaign not found"))
    # Do not auto-transition state; publishing only allowed from approved or scheduled.
    if obj.status not in {"approved", "scheduled"}:
        raise ConflictError(f"Campaign cannot be published from status '{obj.status}'")
    if not obj.starts_at:
        obj.starts_at = datetime.now(timezone.utc)
        db.commit()
    report = publish_campaign(db, campaign_id=str(obj.id), actor_id=user.id, scheduled_at=obj.starts_at)
    db.refresh(obj)
    _audit(db, request, user, "publish", obj)
    return ok({
        **_serialize(obj),
        "execution": {
            "channels": report.channels,
            "deliveries": report.deliveries,
            "recipientCount": report.recipient_count,
        },
    })



@router.post("/{cid}/archive")
def archive(cid: str, request: Request, db: Session = Depends(get_db),
            user: User = Depends(require_perm("campaign:edit"))):
    obj = campaigns.get(db, cid) or (_ for _ in ()).throw(NotFoundError("Campaign not found"))
    _transition(obj, "archived")
    db.commit(); db.refresh(obj)
    _audit(db, request, user, "archive", obj)
    return ok(_serialize(obj))


@router.post("/{cid}/clone", status_code=201)
def clone(cid: str, request: Request, db: Session = Depends(get_db),
          user: User = Depends(require_perm("campaign:create"))):
    src = campaigns.get(db, cid) or (_ for _ in ()).throw(NotFoundError("Campaign not found"))
    dup = Campaign(
        workspace_id=src.workspace_id, name=f"{src.name} (copy)", status="draft",
        channels=list(src.channels or []), audience_count=src.audience_count,
        owner_id=user.id,
    )
    db.add(dup); db.commit(); db.refresh(dup)
    _audit(db, request, user, "clone", dup)
    return ok(_serialize(dup))


@router.get("/{cid}/approvals")
def approvals(cid: str, db: Session = Depends(get_db),
              _: User = Depends(require_perm("campaign:view"))):
    from sqlalchemy import select
    rows = db.scalars(select(Approval).where(Approval.campaign_id == cid)
                      .order_by(Approval.created_at.desc())).all()
    return ok({"items": [
        {"id": str(a.id), "status": a.status, "reviewerId": str(a.reviewer_id) if a.reviewer_id else None,
         "note": a.note, "createdAt": a.created_at.isoformat()} for a in rows
    ]})


# --- Campaign audience assignment endpoints ---


@router.post("/{cid}/audience", status_code=201)
def add_audience(cid: str, payload: CampaignAudienceRequest, request: Request,
                 db: Session = Depends(get_db),
                 user: User = Depends(require_perm("campaign:edit"))):
    obj = campaigns.get(db, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload
    audience_ids = data.get("audienceIds") or []
    if not audience_ids:
        raise ValidationError("audienceIds is required")

    try:
        added, skipped, count = campaign_assign_repo.add_audience(db, cid, [str(x) for x in audience_ids])
        db.commit()
    except Exception:
        db.rollback()
        raise
    _audit(db, request, user, "assign_audience", obj)
    return ok({"audienceCount": count, "added": added, "skipped": skipped})


@router.get("/{cid}/audience")
def list_audience(cid: str, pp: PageParams = Depends(page_params), db: Session = Depends(get_db),
                  _: User = Depends(require_perm("campaign:view"))):
    items, total = campaign_assign_repo.list_audience(db, cid, page=pp.page, page_size=pp.page_size, search=pp.search)
    # simple serializer
    def _serialize_a(a):
        return {
            "id": str(a.id),
            "fullName": a.full_name,
            "email": a.email,
            "phone": a.phone,
            "language": a.language,
        }
    return paginated([_serialize_a(x) for x in items], pp.page, pp.page_size, total)


@router.delete("/{cid}/audience/{audience_id}")
def delete_audience(cid: str, audience_id: str, request: Request,
                    db: Session = Depends(get_db),
                    user: User = Depends(require_perm("campaign:edit"))):
    obj = campaigns.get(db, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    try:
        removed, count = campaign_assign_repo.remove_audience(db, cid, audience_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    _audit(db, request, user, "remove_audience", obj)
    return ok({"audienceCount": count})


# --- Campaign template assignment endpoints ---


@router.post("/{cid}/templates", status_code=201)
def add_template(cid: str, payload: CampaignTemplateRequest, request: Request,
                 db: Session = Depends(get_db),
                 user: User = Depends(require_perm("campaign:edit"))):
    obj = campaigns.get(db, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload
    template_id = str(data.get("templateId"))
    channel = data.get("channel")
    if not template_id or not channel:
        raise ValidationError("templateId and channel are required")
    try:
        added = campaign_assign_repo.add_template(db, cid, template_id, channel)
        db.commit()
    except Exception:
        db.rollback()
        raise
    _audit(db, request, user, "assign_template", obj)
    # return assigned templates with metadata
    rows = campaign_assign_repo.list_templates(db, cid)
    return ok({"items": rows})


@router.get("/{cid}/templates")
def list_templates(cid: str, db: Session = Depends(get_db),
                   _: User = Depends(require_perm("campaign:view"))):
    obj = campaigns.get(db, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    rows = campaign_assign_repo.list_templates(db, cid)
    return ok({"items": rows})


@router.delete("/{cid}/templates/{template_id}")
def delete_template(cid: str, template_id: str, request: Request, channel: str = Query(...),
                    db: Session = Depends(get_db),
                    user: User = Depends(require_perm("campaign:edit"))):
    obj = campaigns.get(db, cid)
    if not obj:
        raise NotFoundError("Campaign not found")
    if not channel:
        raise ValidationError("channel query parameter is required to remove template assignment")
    try:
        removed = campaign_assign_repo.remove_template(db, cid, template_id, channel)
        db.commit()
    except Exception:
        db.rollback()
        raise
    _audit(db, request, user, "remove_template", obj)
    return ok({"removed": True})
