"""Notification service.

Persists notifications, records delivery history, supports user
preferences (channel enable/disable + quiet-hours), and enqueues
real delivery via the communication providers.
"""
from __future__ import annotations

import uuid
from datetime import datetime, time as dtime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationPreference


def _within_quiet_hours(prefs: NotificationPreference | None) -> bool:
    if not prefs or not prefs.quiet_hours:
        return False
    start = prefs.quiet_hours.get("start")
    end = prefs.quiet_hours.get("end")
    if not start or not end:
        return False
    now = datetime.now(timezone.utc).time()
    try:
        s = dtime.fromisoformat(start)
        e = dtime.fromisoformat(end)
    except ValueError:
        return False
    if s <= e:
        return s <= now <= e
    return now >= s or now <= e


def get_preferences(db: Session, user_id: str) -> list[NotificationPreference]:
    return list(db.scalars(select(NotificationPreference).where(NotificationPreference.user_id == user_id)))


def is_channel_enabled(db: Session, user_id: str, channel: str) -> bool:
    pref = db.scalar(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == user_id, NotificationPreference.channel == channel)
    )
    if pref is None:
        return True
    return pref.enabled and not _within_quiet_hours(pref)


def create(
    db: Session,
    *,
    user_id: str,
    title: str,
    message: str,
    category: str = "system",
    priority: str = "normal",
    href: str | None = None,
) -> Notification:
    notif = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        priority=priority,
        href=href,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def broadcast(db: Session, *, user_ids: Iterable[str], title: str, message: str, category: str = "system", priority: str = "normal") -> int:
    count = 0
    for uid in user_ids:
        create(db, user_id=uid, title=title, message=message, category=category, priority=priority)
        count += 1
    return count


def mark_read(db: Session, notification_id: str, *, read: bool = True) -> Notification | None:
    n = db.get(Notification, notification_id)
    if not n:
        return None
    n.read = read
    db.commit()
    db.refresh(n)
    return n


def mark_all_read(db: Session, user_id: str) -> int:
    rows = db.query(Notification).filter(Notification.user_id == user_id, Notification.read.is_(False)).all()
    for r in rows:
        r.read = True
    db.commit()
    return len(rows)


def digest_for_user(db: Session, user_id: str) -> dict:
    unread = db.query(Notification).filter(Notification.user_id == user_id, Notification.read.is_(False)).all()
    by_priority: dict[str, int] = {}
    for n in unread:
        by_priority[n.priority] = by_priority.get(n.priority, 0) + 1
    return {
        "unreadCount": len(unread),
        "byPriority": by_priority,
        "latest": [
            {"id": str(n.id), "title": n.title, "message": n.message, "createdAt": n.created_at.isoformat()}
            for n in unread[:10]
        ],
    }
