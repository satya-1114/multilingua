"""Production-grade authentication service.

Handles registration, login, refresh-with-rotation, logout, forgot/reset
password, email verification, OTP verification, password change, account
lockout, and session management with device tracking.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.models.auth_extras import (
    AccountLockout,
    LoginAttempt,
    PasswordHistory,
    TrustedDevice,
    VerificationToken,
)
from app.models.security import SecurityEvent
from app.models.user import Role, Session as SessionModel, User, UserRole
from app.security.jwt import create_access_token, create_refresh_token, decode_token
from app.security.password_policy import (
    DEFAULT_POLICY,
    PasswordPolicy,
    strength_score,
    validate_password,
)
from app.security.passwords import hash_password, verify_password

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
PASSWORD_RESET_TTL_MIN = 30
EMAIL_VERIFY_TTL_HOURS = 48
OTP_TTL_MIN = 10


# --------------------------------------------------------------------------- helpers


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _hash_refresh(token: str) -> str:
    return _hash_token(token)


def _extract_device(ua: str | None) -> dict[str, str]:
    ua = ua or ""
    browser = "unknown"
    for name in ("Firefox", "Chrome", "Safari", "Edge", "Opera"):
        if name in ua:
            browser = name
            break
    os_name = "unknown"
    for pattern, label in (
        (r"Windows NT", "Windows"),
        (r"Mac OS X", "macOS"),
        (r"Android", "Android"),
        (r"iPhone|iPad|iOS", "iOS"),
        (r"Linux", "Linux"),
    ):
        if re.search(pattern, ua):
            os_name = label
            break
    device_type = "mobile" if re.search(r"Android|iPhone|iPad", ua) else "browser"
    return {"browser": browser, "os": os_name, "device_type": device_type}


def _get_or_create_lockout(db: Session, user: User) -> AccountLockout:
    row = db.query(AccountLockout).filter(AccountLockout.user_id == user.id).one_or_none()
    if not row:
        row = AccountLockout(user_id=user.id, failed_attempts=0)
        db.add(row)
        db.flush()
    return row


def _record_login_attempt(db: Session, *, email: str, user: User | None, ip: str | None, ua: str | None, success: bool, reason: str | None = None) -> None:
    db.add(LoginAttempt(
        email=email, user_id=user.id if user else None,
        ip_address=ip, user_agent=ua, success=success, reason=reason,
    ))


def _record_security_event(db: Session, *, actor: str, event: str, severity: str = "info", ip: str = "", detail: str = "") -> None:
    db.add(SecurityEvent(actor=actor, event=event, severity=severity, ip=ip or "", detail=detail or ""))


# --------------------------------------------------------------------------- password history


def _prior_password_hashes(db: Session, user_id, limit: int) -> list[str]:
    rows = (
        db.query(PasswordHistory)
        .filter(PasswordHistory.user_id == user_id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return [r.hashed_password for r in rows]


def _persist_password(db: Session, user: User, plain: str, *, policy: PasswordPolicy = DEFAULT_POLICY) -> None:
    validate_password(plain, policy=policy)
    prior = _prior_password_hashes(db, user.id, policy.history_size)
    for h in prior:
        if verify_password(plain, h):
            raise ValidationError("Password has been used recently", details={"code": "password_reuse"})
    if user.hashed_password and verify_password(plain, user.hashed_password):
        raise ValidationError("New password must differ from the current password", details={"code": "password_reuse"})
    new_hash = hash_password(plain)
    user.hashed_password = new_hash
    db.add(PasswordHistory(user_id=user.id, hashed_password=new_hash))


# --------------------------------------------------------------------------- registration


ALLOWED_REGISTRATION_ROLES: frozenset[str] = frozenset(
    {"viewer", "volunteer", "campaign_manager"}
)


_ROLE_DESCRIPTIONS: dict[str, str] = {
    "viewer": "Read-only access",
    "volunteer": "Field volunteer — acts on assigned tasks",
    "campaign_manager": "Plans and launches campaigns",
}


def register(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role: str | None = None,
    ip: str | None = None,
) -> User:
    email_norm = email.lower().strip()
    if db.query(User).filter(func.lower(User.email) == email_norm).first():
        raise ConflictError("Email is already registered")
    validate_password(password)
    user = User(email=email_norm, full_name=full_name, hashed_password=hash_password(password))
    db.add(user)
    db.flush()
    # Self-registration is limited to a safe subset. Privileged roles must
    # be granted by an admin after account creation.
    desired = (role or "viewer").strip().lower()
    if desired not in ALLOWED_REGISTRATION_ROLES:
        desired = "viewer"
    role_row = db.query(Role).filter(Role.name == desired).first()
    if not role_row:
        role_row = Role(
            name=desired,
            description=_ROLE_DESCRIPTIONS.get(desired, desired.replace("_", " ").title()),
        )
        db.add(role_row)
        db.flush()
    db.add(UserRole(user_id=user.id, role_id=role_row.id))
    db.add(PasswordHistory(user_id=user.id, hashed_password=user.hashed_password))
    _record_security_event(db, actor=str(user.id), event="user.registered", ip=ip or "")
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- login


def authenticate(db: Session, *, email: str, password: str, ip: str | None = None, ua: str | None = None) -> User:
    email_norm = email.lower().strip()
    user = db.query(User).filter(func.lower(User.email) == email_norm, User.deleted_at.is_(None)).first()

    if user:
        lockout = _get_or_create_lockout(db, user)
        if lockout.locked_until and lockout.locked_until > _now():
            _record_login_attempt(db, email=email_norm, user=user, ip=ip, ua=ua, success=False, reason="locked")
            _record_security_event(db, actor=str(user.id), event="login.blocked", severity="warning", ip=ip or "")
            db.commit()
            raise ForbiddenError("Account is temporarily locked. Try again later.")

    if not user or not verify_password(password, user.hashed_password):
        if user:
            lockout = _get_or_create_lockout(db, user)
            lockout.failed_attempts += 1
            if lockout.failed_attempts >= MAX_FAILED_ATTEMPTS:
                lockout.locked_until = _now() + timedelta(minutes=LOCKOUT_MINUTES)
                lockout.reason = "too_many_failed_attempts"
                _record_security_event(
                    db, actor=str(user.id), event="account.locked",
                    severity="warning", ip=ip or "", detail=f"{lockout.failed_attempts} failed attempts",
                )
        _record_login_attempt(db, email=email_norm, user=user, ip=ip, ua=ua, success=False, reason="invalid_credentials")
        db.commit()
        raise UnauthorizedError("Invalid email or password")

    if not user.is_active:
        _record_login_attempt(db, email=email_norm, user=user, ip=ip, ua=ua, success=False, reason="suspended")
        db.commit()
        raise UnauthorizedError("Account is suspended")

    lockout = _get_or_create_lockout(db, user)
    lockout.failed_attempts = 0
    lockout.locked_until = None
    _record_login_attempt(db, email=email_norm, user=user, ip=ip, ua=ua, success=True)
    _record_security_event(db, actor=str(user.id), event="login.success", ip=ip or "")
    db.commit()
    return user


# --------------------------------------------------------------------------- tokens


def issue_tokens(
    db: Session, user: User, *,
    ip: str | None = None, ua: str | None = None,
    device_id: str | None = None, remember: bool = False,
) -> dict[str, Any]:
    roles = [r.name for r in user.roles]
    access = create_access_token(str(user.id), roles=roles, workspace_id=str(user.default_workspace_id) if user.default_workspace_id else None)
    refresh = create_refresh_token(str(user.id))
    lifetime_days = settings.APP_REFRESH_TOKEN_DAYS * (2 if remember else 1)
    expires_at = _now() + timedelta(days=lifetime_days)
    session = SessionModel(
        user_id=user.id,
        refresh_token_hash=_hash_refresh(refresh),
        ip_address=ip,
        user_agent=ua,
        expires_at=expires_at,
    )
    db.add(session)

    if device_id:
        device = (
            db.query(TrustedDevice)
            .filter(TrustedDevice.user_id == user.id, TrustedDevice.device_id == device_id)
            .one_or_none()
        )
        info = _extract_device(ua)
        if not device:
            device = TrustedDevice(
                user_id=user.id, device_id=device_id, label=info["browser"] + " on " + info["os"],
                device_type=info["device_type"], browser=info["browser"], operating_system=info["os"],
            )
            db.add(device)
        device.last_seen_at = _now()

    db.commit()
    return {
        "accessToken": access,
        "refreshToken": refresh,
        "tokenType": "Bearer",
        "expiresAt": _now() + timedelta(minutes=settings.APP_ACCESS_TOKEN_MINUTES),
        "sessionId": str(session.id),
    }


def refresh_tokens(db: Session, refresh_token: str, *, ip: str | None = None, ua: str | None = None) -> dict[str, Any]:
    try:
        payload = decode_token(refresh_token, expected="refresh")
    except ValueError as exc:
        raise UnauthorizedError("Invalid refresh token") from exc
    user = db.get(User, payload["sub"])
    if not user or user.deleted_at is not None or not user.is_active:
        raise UnauthorizedError("User not found")
    hashed = _hash_refresh(refresh_token)
    session = (
        db.query(SessionModel)
        .filter(SessionModel.refresh_token_hash == hashed, SessionModel.revoked_at.is_(None))
        .first()
    )
    if not session or session.expires_at < _now():
        # Rotation-reuse: token was seen after revocation → revoke every session.
        db.query(SessionModel).filter(SessionModel.user_id == user.id, SessionModel.revoked_at.is_(None)).update(
            {SessionModel.revoked_at: _now()}
        )
        _record_security_event(db, actor=str(user.id), event="refresh.reuse_detected", severity="critical", ip=ip or "")
        db.commit()
        raise UnauthorizedError("Session expired")
    session.revoked_at = _now()
    db.commit()
    return issue_tokens(db, user, ip=ip, ua=ua)


def revoke(db: Session, refresh_token: str) -> None:
    db.query(SessionModel).filter(SessionModel.refresh_token_hash == _hash_refresh(refresh_token)).update(
        {SessionModel.revoked_at: _now()}
    )
    db.commit()


def revoke_all(db: Session, user_id, *, except_session_id: str | None = None) -> int:
    q = db.query(SessionModel).filter(SessionModel.user_id == user_id, SessionModel.revoked_at.is_(None))
    if except_session_id:
        q = q.filter(SessionModel.id != except_session_id)
    count = q.update({SessionModel.revoked_at: _now()})
    db.commit()
    return count


def cleanup_inactive_sessions(db: Session) -> int:
    """Purge revoked or expired sessions older than 30 days."""
    cutoff = _now() - timedelta(days=30)
    q = db.query(SessionModel).filter(
        ((SessionModel.revoked_at.isnot(None)) | (SessionModel.expires_at < _now())),
        SessionModel.created_at < cutoff,
    )
    n = q.delete(synchronize_session=False)
    db.commit()
    return n


# --------------------------------------------------------------------------- password change


def change_password(db: Session, user: User, *, current: str, new: str) -> None:
    if not verify_password(current, user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")
    _persist_password(db, user, new)
    revoke_all(db, user.id)
    _record_security_event(db, actor=str(user.id), event="password.changed", severity="warning")
    db.commit()


# --------------------------------------------------------------------------- password reset


def create_password_reset(db: Session, email: str, *, ip: str | None = None) -> str | None:
    """Returns the raw reset token (deliver by email). Silent when user is absent."""
    user = db.query(User).filter(func.lower(User.email) == email.lower().strip()).first()
    if not user:
        return None
    raw = secrets.token_urlsafe(32)
    token = VerificationToken(
        user_id=user.id, purpose="password_reset",
        token_hash=_hash_token(raw),
        expires_at=_now() + timedelta(minutes=PASSWORD_RESET_TTL_MIN),
        ip_address=ip,
    )
    db.add(token)
    _record_security_event(db, actor=str(user.id), event="password.reset_requested", ip=ip or "")
    db.commit()
    return raw


def reset_password(db: Session, *, token: str, new_password: str) -> None:
    row = _consume_token(db, token=token, purpose="password_reset")
    user = db.get(User, row.user_id)
    if not user:
        raise NotFoundError("User not found")
    _persist_password(db, user, new_password)
    revoke_all(db, user.id)
    _record_security_event(db, actor=str(user.id), event="password.reset", severity="warning")
    db.commit()


# --------------------------------------------------------------------------- email verification


def create_email_verification(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(VerificationToken(
        user_id=user.id, purpose="email_verify",
        token_hash=_hash_token(raw),
        expires_at=_now() + timedelta(hours=EMAIL_VERIFY_TTL_HOURS),
    ))
    db.commit()
    return raw


def verify_email(db: Session, token: str) -> User:
    row = _consume_token(db, token=token, purpose="email_verify")
    user = db.get(User, row.user_id)
    if not user:
        raise NotFoundError("User not found")
    user.email_verified_at = _now()
    _record_security_event(db, actor=str(user.id), event="email.verified")
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- OTP


def create_otp(db: Session, email: str) -> str | None:
    user = db.query(User).filter(func.lower(User.email) == email.lower().strip()).first()
    if not user:
        return None
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(VerificationToken(
        user_id=user.id, purpose="otp",
        token_hash=_hash_token(code),
        expires_at=_now() + timedelta(minutes=OTP_TTL_MIN),
    ))
    db.commit()
    return code


def verify_otp(db: Session, *, email: str, code: str) -> User:
    user = db.query(User).filter(func.lower(User.email) == email.lower().strip()).first()
    if not user:
        raise NotFoundError("User not found")
    row = (
        db.query(VerificationToken)
        .filter(
            VerificationToken.user_id == user.id,
            VerificationToken.purpose == "otp",
            VerificationToken.token_hash == _hash_token(code),
            VerificationToken.consumed_at.is_(None),
        )
        .first()
    )
    if not row or row.expires_at < _now():
        raise UnauthorizedError("Invalid or expired code")
    row.consumed_at = _now()
    db.commit()
    return user


# --------------------------------------------------------------------------- token consumption


def _consume_token(db: Session, *, token: str, purpose: str) -> VerificationToken:
    row = (
        db.query(VerificationToken)
        .filter(
            VerificationToken.purpose == purpose,
            VerificationToken.token_hash == _hash_token(token),
            VerificationToken.consumed_at.is_(None),
        )
        .first()
    )
    if not row or row.expires_at < _now():
        raise UnauthorizedError(f"Invalid or expired {purpose.replace('_', ' ')} token")
    row.consumed_at = _now()
    db.flush()
    return row


# --------------------------------------------------------------------------- account admin


def lock_account(db: Session, user: User, *, reason: str, minutes: int = 60) -> None:
    row = _get_or_create_lockout(db, user)
    row.locked_until = _now() + timedelta(minutes=minutes)
    row.reason = reason
    _record_security_event(db, actor=str(user.id), event="account.locked", severity="warning", detail=reason)
    db.commit()


def unlock_account(db: Session, user: User) -> None:
    row = _get_or_create_lockout(db, user)
    row.locked_until = None
    row.failed_attempts = 0
    row.reason = None
    _record_security_event(db, actor=str(user.id), event="account.unlocked")
    db.commit()


# --------------------------------------------------------------------------- misc


def password_strength(password: str) -> int:
    return strength_score(password)
