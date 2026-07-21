"""Production AuditHandler (Phase 8.4)."""
from __future__ import annotations

import uuid
from typing import Any

from app.constants.workflow import ACTION_TYPE_AUDIT
from app.runtime.action_handlers._base import (
    BusinessError,
    ConfigurationError,
    ProductionActionHandler,
)
from app.runtime.context import WorkflowExecutionContext

ALLOWED_SEVERITIES: tuple[str, ...] = ("info", "notice", "warning", "critical")


class AuditHandler(ProductionActionHandler):
    action_type = ACTION_TYPE_AUDIT
    entity = "audit_log"
    required_keys = ("event",)

    def validate(self, config: dict[str, Any]) -> None:
        super().validate(config)
        event = str(config.get("event") or "").strip()
        if len(event) > 80:
            raise ConfigurationError(
                "audit: event exceeds 80 characters",
                details={"length": len(event)},
            )
        module = config.get("module")
        if module is not None and (not isinstance(module, str) or len(module) > 50):
            raise ConfigurationError(
                "audit: module must be a string ≤ 50 characters",
                details={"module": module},
            )
        severity = config.get("severity", "info")
        if severity not in ALLOWED_SEVERITIES:
            raise ConfigurationError(
                "audit: invalid severity",
                details={"severity": severity, "allowed": list(ALLOWED_SEVERITIES)},
            )
        metadata = config.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ConfigurationError(
                "audit: metadata must be an object",
                details={"got": type(metadata).__name__},
            )

    def run(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        from app.services import audit as audit_service

        event = str(config["event"]).strip()
        module = str(config.get("module") or "workflow")
        severity = str(config.get("severity") or "info")
        category = config.get("category")
        entity_id = config.get("entity_id")
        entity_label = config.get("entity_label")

        metadata: dict[str, Any] = {
            "workflowId": context.workflow_id,
            "executionId": context.execution_id,
            "triggerEvent": context.trigger_event,
            "severity": severity,
        }
        if category:
            metadata["category"] = str(category)
        extra = config.get("metadata")
        if isinstance(extra, dict):
            metadata.update(extra)

        try:
            entry = audit_service.log(
                context.db,
                action=event,
                module=module,
                actor_id=_coerce_uuid(context.actor_id),
                workspace_id=_coerce_uuid(context.organization_id),
                entity_id=str(entity_id) if entity_id is not None else None,
                entity_label=str(entity_label) if entity_label else None,
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001
            raise BusinessError(
                f"audit persistence failed: {exc}",
                details={"action": event, "module": module},
            ) from exc

        return {
            "auditId": str(entry.id),
            "action": event,
            "module": module,
            "severity": severity,
        }


def _coerce_uuid(value: Any) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


__all__ = ["AuditHandler"]