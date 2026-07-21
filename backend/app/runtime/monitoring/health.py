"""Runtime health checks (Phase 8.5)."""
from __future__ import annotations

from typing import Any

from app.runtime.registry import ActionRegistry, default_registry


STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"
STATUS_UNHEALTHY = "unhealthy"
STATUS_UNKNOWN = "unknown"


def _worst(statuses: list[str]) -> str:
    order = {STATUS_OK: 0, STATUS_UNKNOWN: 1, STATUS_DEGRADED: 2, STATUS_UNHEALTHY: 3}
    if not statuses:
        return STATUS_UNKNOWN
    return max(statuses, key=lambda s: order.get(s, 1))


class WorkflowRuntimeHealth:
    """Perform a best-effort health check across runtime subsystems."""

    def __init__(
        self,
        *,
        registry: ActionRegistry | None = None,
        expected_handlers: tuple[str, ...] | None = None,
    ) -> None:
        self.registry = registry or default_registry
        self.expected_handlers = expected_handlers or (
            "notification",
            "audit",
            "analytics",
            "webhook",
            "update_entity",
        )

    def _check_registry(self) -> dict[str, Any]:
        registered = self.registry.registered_types()
        if not registered:
            return {
                "status": STATUS_UNHEALTHY,
                "detail": "no action handlers registered",
                "registered": [],
            }
        missing = [h for h in self.expected_handlers if h not in registered]
        if missing:
            return {
                "status": STATUS_DEGRADED,
                "detail": "missing expected handlers",
                "missing": missing,
                "registered": registered,
            }
        return {"status": STATUS_OK, "registered": registered}

    def _check_scheduler(self) -> dict[str, Any]:
        try:
            from app.runtime.scheduler import scheduler as _sched  # noqa: F401

            return {"status": STATUS_OK, "detail": "scheduler module importable"}
        except Exception as exc:  # noqa: BLE001
            return {"status": STATUS_DEGRADED, "detail": f"scheduler unavailable: {exc}"}

    def _check_queue(self) -> dict[str, Any]:
        try:
            from app.runtime.scheduler.queue import default_workflow_queue

            queue = default_workflow_queue()
            return {"status": STATUS_OK, "backend": type(queue).__name__}
        except Exception as exc:  # noqa: BLE001
            return {"status": STATUS_UNHEALTHY, "detail": f"queue unavailable: {exc}"}

    def _check_celery(self) -> dict[str, Any]:
        try:
            from app.runtime.scheduler.celery_app import workflow_celery_app

            try:
                pong = workflow_celery_app.control.ping(timeout=0.1)
            except Exception as exc:  # noqa: BLE001
                return {"status": STATUS_UNKNOWN, "detail": f"broker unreachable: {exc}"}
            if not pong:
                return {"status": STATUS_UNKNOWN, "detail": "no workers responded"}
            return {"status": STATUS_OK, "workers": len(pong)}
        except Exception as exc:  # noqa: BLE001
            return {"status": STATUS_UNKNOWN, "detail": f"celery unavailable: {exc}"}

    def _check_handlers(self) -> dict[str, Any]:
        registered = self.registry.registered_types()
        return {
            "status": STATUS_OK if registered else STATUS_UNHEALTHY,
            "count": len(registered),
            "handlers": registered,
        }

    def _check_leader(self) -> dict[str, Any]:
        try:
            from app.runtime.ha.election import default_elector

            elector = default_elector()
            status = elector.status().to_dict()
            return {
                "status": STATUS_OK,
                "isLeader": status["isLeader"],
                "nodeId": status["nodeId"],
                "provider": status["provider"],
                "leaseExpiresAt": status["leaseExpiresAt"],
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": STATUS_DEGRADED, "detail": f"leader unavailable: {exc}"}

    def _check_lock_provider(self) -> dict[str, Any]:
        try:
            from app.runtime.ha.locking import default_lock_provider

            provider = default_lock_provider()
            healthy = bool(provider.is_healthy())
            return {
                "status": STATUS_OK if healthy else STATUS_DEGRADED,
                "provider": type(provider).__name__,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": STATUS_UNHEALTHY, "detail": f"lock provider unavailable: {exc}"}

    def _check_idempotency(self) -> dict[str, Any]:
        try:
            from app.runtime.ha.idempotency import default_idempotency_store

            store = default_idempotency_store()
            return {"status": STATUS_OK, "provider": type(store).__name__}
        except Exception as exc:  # noqa: BLE001
            return {"status": STATUS_DEGRADED, "detail": f"idempotency unavailable: {exc}"}

    def check(self) -> dict[str, Any]:
        checks = {
            "registry": self._check_registry(),
            "scheduler": self._check_scheduler(),
            "queue": self._check_queue(),
            "celery": self._check_celery(),
            "handlers": self._check_handlers(),
            "leader": self._check_leader(),
            "lockProvider": self._check_lock_provider(),
            "idempotency": self._check_idempotency(),
        }
        overall_inputs = [
            checks["registry"]["status"],
            checks["scheduler"]["status"],
            checks["queue"]["status"],
            checks["handlers"]["status"],
            checks["lockProvider"]["status"],
            checks["idempotency"]["status"],
        ]
        return {"status": _worst(overall_inputs), "checks": checks}


default_runtime_health = WorkflowRuntimeHealth()


__all__ = [
    "STATUS_OK",
    "STATUS_DEGRADED",
    "STATUS_UNHEALTHY",
    "STATUS_UNKNOWN",
    "WorkflowRuntimeHealth",
    "default_runtime_health",
]