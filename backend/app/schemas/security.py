from __future__ import annotations

from app.schemas.common import IdentifiedDto


class SessionDto(IdentifiedDto):
    ipAddress: str | None = None
    userAgent: str | None = None


class SecurityEventDto(IdentifiedDto):
    actor: str
    severity: str
    event: str
    ip: str
