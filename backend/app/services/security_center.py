"""Session, device, and security-center query services."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.models.auth_extras import AccountLockout, LoginAttempt, TrustedDevice, VerificationToken
from app.models.security import SecurityEvent
from app.models.user import Session as SessionModel, User


def _now():
    return datetime.now(timezone.utc)


def active_sessions(db: DbSession, user: User) -> list[dict[str, Any]]:
    rows = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user.id, SessionModel.revoked_at.is_(None), SessionModel.expires_at > _now())
        .order_by(SessionModel.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(s.id),
            "ipAddress": s.ip_address,
            "userAgent": s.user_agent,
            "createdAt": s.created_at.isoformat(),
            "expiresAt": s.expires_at.isoformat(),
        }
        for s in rows
    ]


def recent_logins(db: DbSession, user: User, limit: int = 25) -> list[dict[str, Any]]:
    rows = (
        db.query(LoginAttempt)
        .filter(LoginAttempt.user_id == user.id)
        .order_by(LoginAttempt.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "success": r.success,
            "reason": r.reason,
            "ipAddress": r.ip_address,
            "userAgent": r.user_agent,
            "createdAt": r.created_at.isoformat(),
        }
        for r in rows
    ]


def failed_logins(db: DbSession, user: User, *, hours: int = 24) -> int:
    cutoff = _now() - timedelta(hours=hours)
    return (
        db.query(func.count(LoginAttempt.id))
        .filter(LoginAttempt.user_id == user.id, LoginAttempt.success.is_(False), LoginAttempt.created_at >= cutoff)
        .scalar()
        or 0
    )


def devices(db: DbSession, user: User) -> list[dict[str, Any]]:
    rows = (
        db.query(TrustedDevice)
        .filter(TrustedDevice.user_id == user.id)
        .order_by(TrustedDevice.last_seen_at.desc().nullslast())
        .all()
    )
    return [
        {
            "id": str(d.id),
            "deviceId": d.device_id,
            "label": d.label,
            "type": d.device_type,
            "browser": d.browser,
            "operatingSystem": d.operating_system,
            "trusted": d.trusted,
            "lastSeenAt": d.last_seen_at.isoformat() if d.last_seen_at else None,
        }
        for d in rows
    ]


def trust_device(db: DbSession, user: User, device_id: str, trusted: bool) -> None:
    row = (
        db.query(TrustedDevice)
        .filter(TrustedDevice.user_id == user.id, TrustedDevice.id == device_id)
        .one_or_none()
    )
    if not row:
        return
    row.trusted = trusted
    db.commit()


def remove_device(db: DbSession, user: User, device_id: str) -> None:
    db.query(TrustedDevice).filter(TrustedDevice.user_id == user.id, TrustedDevice.id == device_id).delete()
    db.commit()


def security_alerts(db: DbSession, user: User, *, limit: int = 25) -> list[dict[str, Any]]:
    rows = (
        db.query(SecurityEvent)
        .filter(SecurityEvent.actor == str(user.id), SecurityEvent.severity.in_(["warning", "critical"]))
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(e.id),
            "event": e.event,
            "severity": e.severity,
            "ipAddress": e.ip,
            "detail": e.detail,
            "createdAt": e.created_at.isoformat(),
        }
        for e in rows
    ]


def security_score(db: DbSession, user: User) -> dict[str, Any]:
    """Simple, deterministic scoring model driven by observable signals."""
    score = 100
    checks: list[dict[str, Any]] = []

    verified = user.email_verified_at is not None
    checks.append({"key": "email_verified", "passed": verified, "weight": 15})
    if not verified:
        score -= 15

    fails = failed_logins(db, user, hours=24)
    ok = fails < 3
    checks.append({"key": "recent_failed_logins", "passed": ok, "weight": 10, "value": fails})
    if not ok:
        score -= 10

    device_count = db.query(func.count(TrustedDevice.id)).filter(TrustedDevice.user_id == user.id).scalar() or 0
    active = db.query(func.count(SessionModel.id)).filter(
        SessionModel.user_id == user.id, SessionModel.revoked_at.is_(None), SessionModel.expires_at > _now()
    ).scalar() or 0
    reasonable = active <= 5
    checks.append({"key": "active_sessions", "passed": reasonable, "weight": 10, "value": active})
    if not reasonable:
        score -= 10

    lockout = db.query(AccountLockout).filter(AccountLockout.user_id == user.id).one_or_none()
    locked = bool(lockout and lockout.locked_until and lockout.locked_until > _now())
    checks.append({"key": "not_locked", "passed": not locked, "weight": 20})
    if locked:
        score -= 20

    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"
    return {
        "score": max(0, score),
        "grade": grade,
        "checks": checks,
        "deviceCount": device_count,
        "activeSessions": active,
    }


def account_status(db: DbSession, user: User) -> dict[str, Any]:
    lockout = db.query(AccountLockout).filter(AccountLockout.user_id == user.id).one_or_none()
    return {
        "active": user.is_active,
        "emailVerified": user.email_verified_at is not None,
        "locked": bool(lockout and lockout.locked_until and lockout.locked_until > _now()),
        "lockedUntil": lockout.locked_until.isoformat() if lockout and lockout.locked_until else None,
        "failedAttempts": lockout.failed_attempts if lockout else 0,
    }


def cleanup_expired_verification(db: DbSession) -> int:
    n = db.query(VerificationToken).filter(VerificationToken.expires_at < _now()).delete(synchronize_session=False)
    db.commit()
    return n
