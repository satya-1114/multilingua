"""FastAPI dependencies for authentication and authorization."""
from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import TokenExpiredError, UnauthorizedError
from app.dependencies.db import get_db
from app.models.auth_extras import AccountLockout
from app.models.user import User
from app.security.jwt import decode_token
from app.security.rbac import require_permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Authentication required")
    try:
        payload = decode_token(token, expected="access")
    except ValueError as exc:
        raise TokenExpiredError("Invalid or expired token") from exc
    user = db.get(User, payload["sub"])
    if not user or user.deleted_at is not None or not user.is_active:
        raise UnauthorizedError("User is not available")
    from datetime import datetime, timezone
    lockout = db.query(AccountLockout).filter(AccountLockout.user_id == user.id).one_or_none()
    if lockout and lockout.locked_until and lockout.locked_until > datetime.now(timezone.utc):
        raise UnauthorizedError("Account is locked")
    return user


def optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        return current_user(token=token, db=db)  # type: ignore[arg-type]
    except UnauthorizedError:
        return None


def require_perm(permission: str):
    def _dep(user: User = Depends(current_user)) -> User:
        roles = [r.name for r in user.roles]
        require_permission(roles, permission)
        return user
    return _dep
