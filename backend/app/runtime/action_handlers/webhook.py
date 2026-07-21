"""Production WebhookHandler (Phase 8.4).

Outbound-only HTTP webhook delivery via :mod:`httpx`. Retryable failures
(network errors, timeouts, 5xx, 429) are surfaced as
:class:`~app.runtime.action_handlers._base.TransientError` so the runtime
can requeue the action.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.constants.workflow import ACTION_TYPE_WEBHOOK
from app.core.config import settings
from app.security import webhooks as webhook_security
from app.runtime.action_handlers._base import (
    BusinessError,
    ConfigurationError,
    ProductionActionHandler,
    TransientError,
)
from app.runtime.context import WorkflowExecutionContext
from app.runtime.ha.idempotency import default_idempotency_store

DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_TIMEOUT_SECONDS = 120.0
DEFAULT_METHOD = "POST"
ALLOWED_METHODS = ("POST", "PUT", "PATCH")
DEFAULT_IDEMPOTENCY_TTL_S = 24 * 60 * 60


class WebhookHandler(ProductionActionHandler):
    action_type = ACTION_TYPE_WEBHOOK
    entity = "webhook"
    required_keys = ("url",)

    #: Injected client factory — override in tests.
    client_factory = staticmethod(httpx.Client)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self, config: dict[str, Any]) -> None:
        super().validate(config)
        url = str(config.get("url") or "")
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ConfigurationError(
                "webhook: url must be http(s)",
                details={"url": url},
            )
        method = str(config.get("method") or DEFAULT_METHOD).upper()
        if method not in ALLOWED_METHODS:
            raise ConfigurationError(
                "webhook: unsupported method",
                details={"method": method, "allowed": list(ALLOWED_METHODS)},
            )
        headers = config.get("headers")
        if headers is not None:
            if not isinstance(headers, dict):
                raise ConfigurationError(
                    "webhook: headers must be an object",
                    details={"got": type(headers).__name__},
                )
            for k, v in headers.items():
                if not isinstance(k, str) or not isinstance(v, (str, int, float)):
                    raise ConfigurationError(
                        "webhook: header keys/values must be scalar",
                        details={"key": k},
                    )
        timeout = config.get("timeout", DEFAULT_TIMEOUT_SECONDS)
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool):
            raise ConfigurationError(
                "webhook: timeout must be numeric",
                details={"got": type(timeout).__name__},
            )
        if timeout <= 0 or timeout > MAX_TIMEOUT_SECONDS:
            raise ConfigurationError(
                "webhook: timeout out of range",
                details={"timeout": timeout, "max": MAX_TIMEOUT_SECONDS},
            )
        payload = config.get("payload")
        if payload is not None and not isinstance(payload, (dict, list)):
            raise ConfigurationError(
                "webhook: payload must be JSON object or array",
                details={"got": type(payload).__name__},
            )

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def run(
        self,
        context: WorkflowExecutionContext,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        url = str(config["url"])
        method = str(config.get("method") or DEFAULT_METHOD).upper()
        timeout = float(config.get("timeout") or DEFAULT_TIMEOUT_SECONDS)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        for k, v in (config.get("headers") or {}).items():
            headers[str(k)] = str(v)
        headers.setdefault(
            "X-Workflow-Id", context.workflow_id
        )
        if context.execution_id:
            headers.setdefault("X-Workflow-Execution-Id", context.execution_id)

        body_payload = config.get("payload")
        if body_payload is None:
            body_payload = {
                "workflowId": context.workflow_id,
                "executionId": context.execution_id,
                "triggerEvent": context.trigger_event,
                "triggerPayload": context.trigger_payload,
            }
        try:
            body_bytes = json.dumps(body_payload).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise BusinessError(
                f"webhook: payload not JSON-serializable: {exc}",
            ) from exc

        # -- Idempotency-Key handling ------------------------------------ #
        idem_key = str(
            config.get("idempotencyKey")
            or config.get("idempotency_key")
            or (context.execution_id or "")
        ).strip()
        if idem_key:
            headers.setdefault("Idempotency-Key", idem_key)
            store = default_idempotency_store()
            ttl = float(config.get("idempotencyTtl") or DEFAULT_IDEMPOTENCY_TTL_S)
            is_new, record = store.remember(
                f"webhook:{url}:{idem_key}", ttl_s=ttl,
            )
            if not is_new:
                return {
                    "url": url,
                    "method": method,
                    "status": 0,
                    "duplicateSuppressed": True,
                    "idempotencyKey": idem_key,
                    "originalStoredAt": record.stored_at,
                }

        secret = str(config.get("secret") or settings.WEBHOOK_SIGNING_SECRET or "")
        if secret:
            try:
                sig_headers = webhook_security.sign(body_bytes, secret)
            except webhook_security.WebhookSecurityError as exc:
                raise ConfigurationError(
                    f"webhook: signing failed: {exc}",
                ) from exc
            for k, v in sig_headers.items():
                headers.setdefault(k, v)

        try:
            with self.client_factory(timeout=timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=headers,
                    content=body_bytes,
                )
        except httpx.TimeoutException as exc:
            raise TransientError(
                f"webhook timed out after {timeout}s",
                details={"url": url, "timeout": timeout},
            ) from exc
        except httpx.TransportError as exc:
            raise TransientError(
                f"webhook transport error: {exc}",
                details={"url": url},
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise BusinessError(
                f"webhook request failed: {exc}",
                details={"url": url},
            ) from exc

        status = response.status_code
        snippet = _safe_snippet(response)
        if status >= 500 or status == 429 or status == 408:
            raise TransientError(
                f"webhook responded {status}",
                details={"url": url, "status": status, "body": snippet},
            )
        if status >= 400:
            raise BusinessError(
                f"webhook responded {status}",
                details={"url": url, "status": status, "body": snippet},
            )

        return {
            "url": url,
            "method": method,
            "status": status,
            "responseSnippet": snippet,
        }


def _safe_snippet(response: httpx.Response, limit: int = 500) -> str:
    try:
        text = response.text or ""
    except Exception:  # pragma: no cover - defensive
        return ""
    return text[:limit]


__all__ = ["WebhookHandler"]