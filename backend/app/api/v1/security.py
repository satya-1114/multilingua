"""Security Center API — sessions, devices, login history, alerts, scoring."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.dependencies.rbac import invalidate_permission_cache, permission_required
from app.models.auth_extras import AccountLockout
from app.models.security import SecurityEvent
from app.models.user import Session as SessionModel, User
from app.schemas.auth import LockAccountRequest, MfaEnrollRequest, MfaVerifyRequest
from app.services import audit as audit_service
from app.services import auth as auth_service
from app.services import mfa as mfa_service
from app.services import security_center as sc_service

router = APIRouter()


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok({
        "score": sc_service.security_score(db, user),
        "account": sc_service.account_status(db, user),
        "sessions": sc_service.active_sessions(db, user),
        "devices": sc_service.devices(db, user),
        "recentLogins": sc_service.recent_logins(db, user, limit=10),
        "alerts": sc_service.security_alerts(db, user, limit=10),
    })


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok(sc_service.active_sessions(db, user))


@router.post("/sessions/{sid}/revoke")
def revoke_session(sid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(SessionModel, sid)
    if not s or s.user_id != user.id:
        return ok({"revoked": False})
    s.revoked_at = datetime.now(timezone.utc)
    db.commit()
    audit_service.log(db, action="session_revoked", module="security", actor_id=user.id, entity_id=sid)
    return ok({"revoked": True})


@router.post("/sessions/revoke-all")
def revoke_all_sessions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = auth_service.revoke_all(db, user.id)
    audit_service.log(db, action="sessions_revoked_all", module="security", actor_id=user.id)
    return ok({"revoked": n})


@router.get("/devices")
def devices(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok(sc_service.devices(db, user))


@router.post("/devices/{device_id}/trust")
def trust_device(device_id: str, trusted: bool = True, db: Session = Depends(get_db), user: User = Depends(current_user)):
    sc_service.trust_device(db, user, device_id, trusted)
    audit_service.log(db, action="device_trust_changed", module="security", actor_id=user.id, entity_id=device_id, metadata={"trusted": trusted})
    return ok({"deviceId": device_id, "trusted": trusted})


@router.delete("/devices/{device_id}")
def remove_device(device_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    sc_service.remove_device(db, user, device_id)
    audit_service.log(db, action="device_removed", module="security", actor_id=user.id, entity_id=device_id)
    return ok({"removed": True})


@router.get("/logins")
def logins(limit: int = Query(25, ge=1, le=200), db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok({
        "recent": sc_service.recent_logins(db, user, limit=limit),
        "failedLast24h": sc_service.failed_logins(db, user, hours=24),
    })


@router.get("/alerts")
def alerts(limit: int = Query(25, ge=1, le=200), db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok(sc_service.security_alerts(db, user, limit=limit))


@router.get("/status")
def status(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok(sc_service.account_status(db, user))


@router.get("/score")
def score(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok(sc_service.security_score(db, user))


# ------- admin ---------------------------------------------------------------


@router.post("/users/{user_id}/lock")
def lock_user(user_id: str, payload: LockAccountRequest, db: Session = Depends(get_db), admin: User = Depends(permission_required("user:manage"))):
    target = db.get(User, user_id)
    if not target:
        return ok({"locked": False})
    auth_service.lock_account(db, target, reason=payload.reason, minutes=payload.minutes)
    invalidate_permission_cache(str(target.id))
    audit_service.log(db, action="account_locked", module="security", actor_id=admin.id, entity_id=user_id, metadata={"reason": payload.reason})
    return ok({"locked": True})


@router.post("/users/{user_id}/unlock")
def unlock_user(user_id: str, db: Session = Depends(get_db), admin: User = Depends(permission_required("user:manage"))):
    target = db.get(User, user_id)
    if not target:
        return ok({"unlocked": False})
    auth_service.unlock_account(db, target)
    invalidate_permission_cache(str(target.id))
    audit_service.log(db, action="account_unlocked", module="security", actor_id=admin.id, entity_id=user_id)
    return ok({"unlocked": True})


@router.get("/events")
def events(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db), _: User = Depends(permission_required("audit:view"))):
    rows = db.query(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(limit).all()
    return ok([
        {"id": str(e.id), "actor": e.actor, "severity": e.severity, "event": e.event,
         "ip": e.ip, "detail": e.detail, "createdAt": e.created_at.isoformat()}
        for e in rows
    ])


# ------- MFA -----------------------------------------------------------------


@router.get("/mfa/factors")
def mfa_factors(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return ok(mfa_service.list_factors(db, user))


@router.post("/mfa/enroll")
def mfa_enroll(payload: MfaEnrollRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    result = mfa_service.enroll_factor(db, user, payload.factorType, label=payload.label)
    audit_service.log(db, action="mfa_enrolled", module="security", actor_id=user.id, metadata={"type": payload.factorType})
    return ok(result)


@router.post("/mfa/verify")
def mfa_verify(payload: MfaVerifyRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    mfa_service.verify_factor(db, user, payload.factorId, payload.code)
    audit_service.log(db, action="mfa_verified", module="security", actor_id=user.id, entity_id=payload.factorId)
    return ok({"verified": True})


@router.delete("/mfa/factors/{factor_id}")
def mfa_disable(factor_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    mfa_service.disable_factor(db, user, factor_id)
    audit_service.log(db, action="mfa_disabled", module="security", actor_id=user.id, entity_id=factor_id)
    return ok({"disabled": True})


@router.post("/mfa/recovery-codes")
def mfa_recovery(db: Session = Depends(get_db), user: User = Depends(current_user)):
    codes = mfa_service.generate_recovery_codes(db, user)
    audit_service.log(db, action="mfa_recovery_generated", module="security", actor_id=user.id)
    return ok({"codes": codes})


# ------- password policy -----------------------------------------------------


@router.get("/password-policy")
def password_policy():
    from app.security.password_policy import DEFAULT_POLICY
    p = DEFAULT_POLICY
    return ok({
        "minLength": p.min_length,
        "maxLength": p.max_length,
        "requireUppercase": p.require_upper,
        "requireLowercase": p.require_lower,
        "requireDigit": p.require_digit,
        "requireSymbol": p.require_symbol,
        "historySize": p.history_size,
        "maxAgeDays": p.max_age_days,
    })
