from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.responses import ok, paginated
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.dependencies.pagination import PageParams, page_params
from app.models.notification import Notification, NotificationPreference
from app.models.user import User
from app.repositories import notifications as notif_repo
from app.schemas.notification import NotificationCreate
from app.services import notifications as notif_service

router = APIRouter()


def _serialize(n: Notification) -> dict:
    return {
        "id": str(n.id), "title": n.title, "message": n.message, "category": n.category,
        "priority": n.priority, "read": n.read, "archived": n.archived, "href": n.href,
        "createdAt": n.created_at.isoformat(), "updatedAt": n.updated_at.isoformat(),
    }


@router.get("")
def list_(pp: PageParams = Depends(page_params), db: Session = Depends(get_db), user: User = Depends(current_user)):
    items, total = notif_repo.list(
        db, page=pp.page, page_size=pp.page_size, filters={"user_id": user.id},
        sort_by=pp.sort_by, sort_dir=pp.sort_dir,
    )
    return paginated([_serialize(x) for x in items], pp.page, pp.page_size, total)


@router.post("", status_code=201)
def create(payload: NotificationCreate, db: Session = Depends(get_db), _: User = Depends(current_user)):
    n = notif_service.create(
        db, user_id=payload.userId, title=payload.title, message=payload.message,
        category=payload.category, priority=payload.priority, href=payload.href,
    )
    return ok(_serialize(n))


@router.post("/{nid}/read")
def mark_read(nid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = notif_service.mark_read(db, nid, read=True)
    if not n or str(n.user_id) != str(user.id):
        raise NotFoundError("Notification not found")
    return ok(_serialize(n))


@router.post("/{nid}/unread")
def mark_unread(nid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = notif_service.mark_read(db, nid, read=False)
    if not n or str(n.user_id) != str(user.id):
        raise NotFoundError("Notification not found")
    return ok(_serialize(n))


@router.post("/read-all")
def read_all(db: Session = Depends(get_db), user: User = Depends(current_user)):
    count = notif_service.mark_all_read(db, str(user.id))
    return ok({"updated": count})


@router.get("/digest")
def digest(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok(notif_service.digest_for_user(db, str(user.id)))


@router.get("/preferences")
def preferences(db: Session = Depends(get_db), user: User = Depends(current_user)):
    prefs = notif_service.get_preferences(db, str(user.id))
    return ok([
        {"id": str(p.id), "channel": p.channel, "enabled": p.enabled, "quietHours": p.quiet_hours or {}}
        for p in prefs
    ])
