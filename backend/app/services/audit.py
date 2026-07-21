from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log(
    db: Session,
    *,
    action: str,
    module: str,
    actor_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    entity_id: str | None = None,
    entity_label: str | None = None,
    ip: str | None = None,
    ua: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        workspace_id=workspace_id,
        action=action,
        module=module,
        entity_id=entity_id,
        entity_label=entity_label,
        ip_address=ip,
        user_agent=ua,
        metadata_=metadata or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------- #
# Security event stream (Phase 9.1)
# ---------------------------------------------------------------------- #
#
# ``security_event`` is a fire-and-forget structured logger used by the
# rate-limit middleware, auth flow, webhook verification, and RBAC
# denials. It never writes to the DB directly because the caller may not
# have a session; the caller can pass ``db`` to also persist the row.

from app.core.logging import get_logger  # noqa: E402  (bottom-of-file util)

_sec_log = get_logger("security")

SECURITY_EVENTS = {
    "login_failure",
    "login_success",
    "permission_denied",
    "rate_limit_exceeded",
    "webhook_signature_invalid",
    "webhook_signature_missing",
    "webhook_replay_detected",
    "webhook_timestamp_expired",
    "secret_config_warning",
    "upload_rejected",
    "token_revoked",
}


def security_event(
    *,
    action: str,
    actor_id: uuid.UUID | None = None,
    ip: str | None = None,
    ua: str | None = None,
    metadata: dict[str, Any] | None = None,
    db: Session | None = None,
    workspace_id: uuid.UUID | None = None,
) -> None:
    """Emit a structured security-event log; optionally persist to audit."""
    payload = {
        "actor_id": str(actor_id) if actor_id else None,
        "ip": ip,
        "ua": ua,
        **(metadata or {}),
    }
    _sec_log.info("security_event", event_action=action, **payload)
    if db is not None:
        try:
            log(
                db,
                action=action,
                module="security",
                actor_id=actor_id,
                workspace_id=workspace_id,
                ip=ip,
                ua=ua,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 - never break the caller
            pass
