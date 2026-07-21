from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt

from app.core.config import settings

ALGO = "HS256"


def _encode(claims: dict[str, Any], expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=ALGO)


def create_access_token(subject: str, *, workspace_id: str | None = None, roles: list[str] | None = None) -> str:
    return _encode(
        {"sub": subject, "type": "access", "ws": workspace_id, "roles": roles or []},
        timedelta(minutes=settings.APP_ACCESS_TOKEN_MINUTES),
    )


def create_refresh_token(subject: str) -> str:
    return _encode({"sub": subject, "type": "refresh"}, timedelta(days=settings.APP_REFRESH_TOKEN_DAYS))


def decode_token(token: str, *, expected: Literal["access", "refresh"] | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGO])
    except JWTError as exc:
        raise ValueError("invalid_token") from exc
    if expected and payload.get("type") != expected:
        raise ValueError("unexpected_token_type")
    return payload
