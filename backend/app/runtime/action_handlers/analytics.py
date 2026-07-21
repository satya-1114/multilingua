"""Production AnalyticsHandler (Phase 8.4)."""
from __future__ import annotations

import uuid
from typing import Any

from app.constants.analytics import METRIC_SCOPE_PLATFORM, METRIC_SCOPES
from app.constants.workflow import ACTION_TYPE_ANALYTICS
from app.runtime.action_handlers._base import (
    BusinessError,
    ConfigurationError,
    ProductionActionHandler,
)
from app.runtime.context import WorkflowExecutionContext


class AnalyticsHandler(ProductionActionHandler):
    action_type = ACTION_TYPE_ANALYTICS
    entity = "analytics_metric"
    required_keys = ("metric",)

    def validate(self, config: dict[str, Any]) -> None:
        super().validate(config)
        metric = str(config.get("metric") or "").strip()
        if len(metric) > 120:
            raise ConfigurationError(
                "analytics: metric name exceeds 120 characters",
                details={"length": len(metric)},
            )
        scope = config.get("scope", METRIC_SCOPE_PLATFORM)
        if scope not in METRIC_SCOPES:
            raise ConfigurationError(
                "analytics: invalid scope",
                details={"scope": scope, "allowed": list(METRIC_SCOPES)},
            )
        value = config.get("value", 0)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ConfigurationError(
                "analytics: value must be numeric",
                details={"got": type(value).__name__},
            )
        dims = config.get("dimensions")
        if dims is not None and not isinstance(dims, dict):
            raise ConfigurationError(
                "analytics: dimensions must be an object",
                details={"got": type(dims).__name__},
            )
        payload = config.get("payload")
        if payload is not None and not isinstance(payload, dict):
            raise ConfigurationError(
                "analytics: payload must be an object",
                details={"got": type(payload).__name__},
            )

    def run(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        from app.services import analytics as analytics_service

        metric = str(config["metric"]).strip()
        scope = str(config.get("scope") or METRIC_SCOPE_PLATFORM)
        value = float(config.get("value") or 0)
        unit = config.get("unit")
        entity_type = config.get("entity_type")
        entity_id = config.get("entity_id")

        metadata: dict[str, Any] = {
            "workflowId": context.workflow_id,
            "executionId": context.execution_id,
            "triggerEvent": context.trigger_event,
        }
        if isinstance(config.get("dimensions"), dict):
            metadata["dimensions"] = config["dimensions"]
        if isinstance(config.get("payload"), dict):
            metadata["payload"] = config["payload"]

        try:
            metric_row = analytics_service.metric_service.record_metric(
                context.db,
                metric_name=metric,
                metric_scope=scope,
                metric_value=value,
                metric_unit=str(unit) if unit else None,
                entity_type=str(entity_type) if entity_type else None,
                entity_id=_coerce_uuid_or_str(entity_id),
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001
            raise BusinessError(
                f"analytics metric emit failed: {exc}",
                details={"metric": metric, "scope": scope},
            ) from exc

        return {
            "metricId": str(metric_row.id),
            "metric": metric,
            "scope": scope,
            "value": value,
        }


def _coerce_uuid_or_str(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return str(value)


__all__ = ["AnalyticsHandler"]