from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import require_perm
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.communication import CommunicationChannel, Delivery, RetryPolicy
from app.models.user import User
from app.repositories import channels, deliveries
from app.schemas.communication import ScheduleRequest
from app.workers.tasks import dispatch as dispatch_task

router = APIRouter()


def _channel(c: CommunicationChannel) -> dict:
    return {
        "id": str(c.id), "kind": c.kind, "name": c.name, "provider": c.provider,
        "enabled": c.enabled, "createdAt": c.created_at.isoformat(), "updatedAt": c.updated_at.isoformat(),
    }


def _delivery(d: Delivery) -> dict:
    return {
        "id": str(d.id), "campaignId": str(d.campaign_id), "channel": d.channel,
        "status": d.status, "scheduledAt": d.scheduled_at.isoformat() if d.scheduled_at else None,
        "attempts": d.attempts, "createdAt": d.created_at.isoformat(), "updatedAt": d.updated_at.isoformat(),
    }


@router.get("/channels")
def list_channels(pp: PageParams = Depends(page_params), db: Session = Depends(get_db), _: User = Depends(require_perm("channel:view"))):
    items, total = channels.list(db, page=pp.page, page_size=pp.page_size, sort_by=pp.sort_by, sort_dir=pp.sort_dir)
    return paginated([_channel(x) for x in items], pp.page, pp.page_size, total)


@router.get("/delivery")
def list_deliveries(pp: PageParams = Depends(page_params), db: Session = Depends(get_db), _: User = Depends(require_perm("delivery:view"))):
    items, total = deliveries.list(db, page=pp.page, page_size=pp.page_size, sort_by=pp.sort_by, sort_dir=pp.sort_dir)
    return paginated([_delivery(x) for x in items], pp.page, pp.page_size, total)


@router.post("/schedule")
def schedule(payload: ScheduleRequest, db: Session = Depends(get_db), _: User = Depends(require_perm("scheduler:manage"))):
    obj = deliveries.create(
        db,
        {
            "campaign_id": payload.campaignId,
            "channel": payload.channel,
            "scheduled_at": payload.scheduledAt,
            "priority": payload.priority,
            "status": "queued",
        },
    )
    dispatch_task.apply_async(args=[str(obj.id)], countdown=1)
    return ok(_delivery(obj))


@router.post("/delivery/{did}/retry")
def retry_delivery(did: str, _: User = Depends(require_perm("delivery:manage"))):
    dispatch_task.apply_async(args=[did], countdown=0)
    return ok({"queued": True})


@router.get("/retry-policies")
def list_retry_policies(db: Session = Depends(get_db), _: User = Depends(require_perm("retry_policy:manage"))):
    rows = db.query(RetryPolicy).all()
    return ok([
        {"id": str(r.id), "channel": r.channel, "maxAttempts": r.max_attempts,
         "backoffSeconds": r.backoff_seconds, "strategy": r.strategy}
        for r in rows
    ])
