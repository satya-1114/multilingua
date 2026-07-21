"""Production action handler tests (Phase 8.4).

Covers NotificationHandler, AuditHandler, AnalyticsHandler,
WebhookHandler and EntityUpdateHandler validation, execution, error
taxonomy and retry semantics.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.constants.workflow import (
    ACTION_TYPE_ANALYTICS,
    ACTION_TYPE_AUDIT,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_UPDATE_ENTITY,
    ACTION_TYPE_WEBHOOK,
    STEP_STATUS_COMPLETED,
)
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.workflow import WorkflowDefinition
from app.runtime.action_handlers import (
    AnalyticsHandler,
    AuditHandler,
    EntityUpdateHandler,
    NotificationHandler,
    WebhookHandler,
)
from app.runtime.action_handlers._base import (
    BusinessError,
    ConfigurationError,
    ProductionActionHandler,
    TransientError,
)
from app.runtime.context import WorkflowExecutionContext
from app.runtime.exceptions import ActionExecutionError
from app.runtime.registry import ActionRegistry
from app.runtime.service import DEFAULT_HANDLERS, WorkflowRuntimeService


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_ctx(
    *,
    db: Any = None,
    dry_run: bool = False,
    organization_id: Any = None,
    actor_id: Any = None,
    metadata: dict[str, Any] | None = None,
) -> WorkflowExecutionContext:
    wf = WorkflowDefinition(
        id=uuid.uuid4(),
        name="wf",
        trigger_type="manual",
        organization_id=organization_id,
    )
    meta = dict(metadata or {})
    if dry_run:
        meta["dry_run"] = True
    return WorkflowExecutionContext(
        workflow=wf,
        execution=None,
        organization_id=organization_id,
        actor_id=actor_id,
        metadata=meta,
        db=db,
    )


class _DummyDB:
    """Marker session — handlers with services will be monkeypatched."""


# =========================================================================== #
# Base scaffolding
# =========================================================================== #


def test_dry_run_short_circuits_notification():
    ctx = _make_ctx(dry_run=True, db=_DummyDB())
    result = NotificationHandler().execute(
        ctx, {"title": "t", "message": "m", "user_id": "u"}
    )
    assert result.success is True
    assert result.status == STEP_STATUS_COMPLETED
    assert result.output["skipped"] is True
    assert result.output["reason"] == "dry_run"


def test_missing_db_short_circuits():
    ctx = _make_ctx()  # no db
    result = AuditHandler().execute(ctx, {"event": "created"})
    assert result.success is True
    assert result.output["reason"] == "no_db"


def test_supports_retry_defaults_true():
    assert NotificationHandler().supports_retry() is True
    assert AuditHandler().supports_retry() is True
    assert AnalyticsHandler().supports_retry() is True
    assert WebhookHandler().supports_retry() is True
    assert EntityUpdateHandler().supports_retry() is True


def test_registry_loads_production_handlers_by_default():
    reg = ActionRegistry()
    svc = WorkflowRuntimeService(registry=reg)
    svc.load_handlers()
    for atype in (
        ACTION_TYPE_NOTIFICATION,
        ACTION_TYPE_AUDIT,
        ACTION_TYPE_ANALYTICS,
        ACTION_TYPE_WEBHOOK,
        ACTION_TYPE_UPDATE_ENTITY,
    ):
        assert reg.has(atype)


def test_registry_supports_custom_registration():
    reg = ActionRegistry()
    svc = WorkflowRuntimeService(registry=reg)
    svc.load_handlers()

    class Custom(ProductionActionHandler):
        action_type = "custom.x"

        def run(self, context, config):  # pragma: no cover - trivial
            return {"ok": True}

    reg.register("custom.x", Custom())
    assert reg.has("custom.x")


def test_default_handlers_tuple_matches_production_set():
    names = {cls.__name__ for cls in DEFAULT_HANDLERS}
    assert names == {
        "NotificationHandler",
        "AuditHandler",
        "AnalyticsHandler",
        "WebhookHandler",
        "EntityUpdateHandler",
    }


def test_base_validate_rejects_non_dict_config():
    with pytest.raises(ValidationError):
        NotificationHandler().validate("nope")  # type: ignore[arg-type]


def test_base_validate_reports_missing_keys():
    with pytest.raises(ValidationError):
        AuditHandler().validate({})


def test_configuration_error_is_validation_error():
    assert issubclass(ConfigurationError, ValidationError)


def test_transient_error_carries_details():
    err = TransientError("boom", details={"a": 1})
    assert err.details == {"a": 1}


def test_business_error_carries_details():
    err = BusinessError("oops", details={"x": 2})
    assert err.details == {"x": 2}


# =========================================================================== #
# NotificationHandler
# =========================================================================== #


class _StubNotif:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, db, *, user_id, title, message, category="system",
               priority="normal", href=None):
        self.calls.append(
            {
                "op": "create",
                "user_id": user_id,
                "title": title,
                "message": message,
                "category": category,
                "priority": priority,
                "href": href,
            }
        )
        return SimpleNamespace(id=uuid.uuid4())

    def broadcast(self, db, *, user_ids, title, message, category="system",
                  priority="normal"):
        ids = list(user_ids)
        for uid in ids:
            self.create(
                db, user_id=uid, title=title, message=message,
                category=category, priority=priority,
            )
        return len(ids)


@pytest.fixture
def notif_stub(monkeypatch):
    stub = _StubNotif()
    import app.services.notifications as _real
    monkeypatch.setattr(_real, "create", stub.create)
    monkeypatch.setattr(_real, "broadcast", stub.broadcast)
    return stub


def test_notification_validate_missing_title():
    with pytest.raises(ValidationError):
        NotificationHandler().validate({"message": "m", "user_id": "u"})


def test_notification_validate_blank_title():
    with pytest.raises(ConfigurationError):
        NotificationHandler().validate(
            {"title": "   ", "message": "m", "user_id": "u"}
        )


def test_notification_validate_title_too_long():
    with pytest.raises(ConfigurationError):
        NotificationHandler().validate(
            {"title": "x" * 500, "message": "m", "user_id": "u"}
        )


def test_notification_validate_message_too_long():
    with pytest.raises(ConfigurationError):
        NotificationHandler().validate(
            {"title": "t", "message": "x" * 5000, "user_id": "u"}
        )


def test_notification_validate_invalid_priority():
    with pytest.raises(ConfigurationError):
        NotificationHandler().validate(
            {"title": "t", "message": "m", "user_id": "u", "priority": "xyz"}
        )


def test_notification_validate_requires_recipient():
    with pytest.raises(ConfigurationError):
        NotificationHandler().validate({"title": "t", "message": "m"})


def test_notification_validate_ok_with_user_id():
    NotificationHandler().validate(
        {"title": "t", "message": "m", "user_id": "u"}
    )


def test_notification_validate_ok_with_broadcast_flag():
    NotificationHandler().validate(
        {"title": "t", "message": "m", "broadcast": True}
    )


def test_notification_single_user_delivery(notif_stub):
    ctx = _make_ctx(db=_DummyDB())
    result = NotificationHandler().execute(
        ctx,
        {
            "title": "Hi",
            "message": "There",
            "user_id": "u-1",
            "priority": "high",
        },
    )
    assert result.success and result.output["delivered"] == 1
    assert notif_stub.calls[0]["user_id"] == "u-1"
    assert notif_stub.calls[0]["priority"] == "high"


def test_notification_multi_user_broadcast(notif_stub):
    ctx = _make_ctx(db=_DummyDB())
    result = NotificationHandler().execute(
        ctx,
        {
            "title": "Hi",
            "message": "There",
            "user_ids": ["a", "b", "c"],
        },
    )
    assert result.output["delivered"] == 3
    assert len(notif_stub.calls) == 3


def test_notification_deduplicates_recipients(notif_stub):
    ctx = _make_ctx(db=_DummyDB())
    NotificationHandler().execute(
        ctx,
        {
            "title": "Hi",
            "message": "There",
            "user_id": "a",
            "user_ids": ["a", "b"],
        },
    )
    delivered = {c["user_id"] for c in notif_stub.calls}
    assert delivered == {"a", "b"}


def test_notification_role_no_matches_raises_business_error(monkeypatch):
    monkeypatch.setattr(
        NotificationHandler, "_users_with_role", lambda self, ctx, role: []
    )
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        NotificationHandler().execute(
            ctx,
            {"title": "t", "message": "m", "role": "admin"},
        )
    assert excinfo.value.retryable is False


def test_notification_service_error_becomes_business_error(monkeypatch):
    import app.services.notifications as _real

    def _boom(*a, **kw):  # noqa: ARG001
        raise RuntimeError("db down")

    monkeypatch.setattr(_real, "create", _boom)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        NotificationHandler().execute(
            ctx, {"title": "t", "message": "m", "user_id": "u"}
        )
    assert excinfo.value.retryable is False


# =========================================================================== #
# AuditHandler
# =========================================================================== #


@pytest.fixture
def audit_stub(monkeypatch):
    calls: list[dict[str, Any]] = []

    def _log(db, **kw):
        calls.append(kw)
        return SimpleNamespace(id=uuid.uuid4())

    import app.services.audit as _real
    monkeypatch.setattr(_real, "log", _log)
    return calls


def test_audit_validate_missing_event():
    with pytest.raises(ValidationError):
        AuditHandler().validate({})


def test_audit_validate_event_too_long():
    with pytest.raises(ConfigurationError):
        AuditHandler().validate({"event": "x" * 200})


def test_audit_validate_bad_module():
    with pytest.raises(ConfigurationError):
        AuditHandler().validate({"event": "e", "module": 42})


def test_audit_validate_bad_severity():
    with pytest.raises(ConfigurationError):
        AuditHandler().validate({"event": "e", "severity": "xxx"})


def test_audit_validate_bad_metadata_type():
    with pytest.raises(ConfigurationError):
        AuditHandler().validate({"event": "e", "metadata": "no"})


def test_audit_validate_ok_defaults():
    AuditHandler().validate({"event": "created"})


def test_audit_execute_logs_via_service(audit_stub):
    ctx = _make_ctx(
        db=_DummyDB(),
        organization_id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
    )
    result = AuditHandler().execute(
        ctx,
        {
            "event": "workflow.tested",
            "module": "workflow",
            "severity": "warning",
            "entity_id": "e-1",
            "metadata": {"extra": True},
        },
    )
    assert result.success
    call = audit_stub[0]
    assert call["action"] == "workflow.tested"
    assert call["module"] == "workflow"
    assert call["entity_id"] == "e-1"
    assert call["metadata"]["severity"] == "warning"
    assert call["metadata"]["extra"] is True
    assert call["metadata"]["workflowId"]


def test_audit_execute_maps_service_failure(monkeypatch):
    import app.services.audit as _real

    def _boom(*a, **kw):  # noqa: ARG001
        raise RuntimeError("no table")

    monkeypatch.setattr(_real, "log", _boom)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        AuditHandler().execute(ctx, {"event": "x"})
    assert excinfo.value.retryable is False


def test_audit_default_module_is_workflow(audit_stub):
    ctx = _make_ctx(db=_DummyDB())
    AuditHandler().execute(ctx, {"event": "e"})
    assert audit_stub[0]["module"] == "workflow"


def test_audit_coerces_uuid_ids(audit_stub):
    org = uuid.uuid4()
    actor = uuid.uuid4()
    ctx = _make_ctx(db=_DummyDB(), organization_id=str(org), actor_id=str(actor))
    AuditHandler().execute(ctx, {"event": "e"})
    call = audit_stub[0]
    assert call["workspace_id"] == org
    assert call["actor_id"] == actor


# =========================================================================== #
# AnalyticsHandler
# =========================================================================== #


@pytest.fixture
def analytics_stub(monkeypatch):
    calls: list[dict[str, Any]] = []

    def _record(db, **kw):
        calls.append(kw)
        return SimpleNamespace(id=uuid.uuid4())

    from app.services.analytics import metric_service
    monkeypatch.setattr(metric_service, "record_metric", _record)
    return calls


def test_analytics_validate_missing_metric():
    with pytest.raises(ValidationError):
        AnalyticsHandler().validate({})


def test_analytics_validate_metric_too_long():
    with pytest.raises(ConfigurationError):
        AnalyticsHandler().validate({"metric": "x" * 200})


def test_analytics_validate_bad_scope():
    with pytest.raises(ConfigurationError):
        AnalyticsHandler().validate({"metric": "m", "scope": "outer_space"})


def test_analytics_validate_non_numeric_value():
    with pytest.raises(ConfigurationError):
        AnalyticsHandler().validate({"metric": "m", "value": "1"})


def test_analytics_validate_bad_dimensions():
    with pytest.raises(ConfigurationError):
        AnalyticsHandler().validate({"metric": "m", "dimensions": []})


def test_analytics_validate_bad_payload():
    with pytest.raises(ConfigurationError):
        AnalyticsHandler().validate({"metric": "m", "payload": 5})


def test_analytics_validate_bool_rejected_as_value():
    with pytest.raises(ConfigurationError):
        AnalyticsHandler().validate({"metric": "m", "value": True})


def test_analytics_execute_records_metric(analytics_stub):
    ctx = _make_ctx(db=_DummyDB())
    result = AnalyticsHandler().execute(
        ctx,
        {
            "metric": "workflow.exec",
            "value": 1.5,
            "unit": "count",
            "dimensions": {"env": "test"},
            "payload": {"note": "hi"},
        },
    )
    assert result.success
    call = analytics_stub[0]
    assert call["metric_name"] == "workflow.exec"
    assert call["metric_value"] == 1.5
    assert call["metric_unit"] == "count"
    assert call["metadata"]["dimensions"] == {"env": "test"}
    assert call["metadata"]["payload"] == {"note": "hi"}


def test_analytics_execute_service_failure(monkeypatch):
    from app.services.analytics import metric_service

    def _boom(db, **kw):  # noqa: ARG001
        raise RuntimeError("emit failed")

    monkeypatch.setattr(metric_service, "record_metric", _boom)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError):
        AnalyticsHandler().execute(ctx, {"metric": "m"})


def test_analytics_entity_id_uuid_coerced(analytics_stub):
    ent = uuid.uuid4()
    ctx = _make_ctx(db=_DummyDB())
    AnalyticsHandler().execute(
        ctx, {"metric": "m", "entity_type": "x", "entity_id": str(ent)}
    )
    assert analytics_stub[0]["entity_id"] == ent


def test_analytics_entity_id_non_uuid_passthrough(analytics_stub):
    ctx = _make_ctx(db=_DummyDB())
    AnalyticsHandler().execute(
        ctx, {"metric": "m", "entity_type": "x", "entity_id": "abc"}
    )
    assert analytics_stub[0]["entity_id"] == "abc"


# =========================================================================== #
# WebhookHandler
# =========================================================================== #


class _FakeResp:
    def __init__(self, status: int, text: str = "ok") -> None:
        self.status_code = status
        self.text = text


class _FakeClient:
    def __init__(
        self,
        *,
        response: _FakeResp | None = None,
        raise_exc: Exception | None = None,
        timeout: float | None = None,
    ) -> None:
        self.response = response or _FakeResp(200)
        self.raise_exc = raise_exc
        self.timeout = timeout
        self.requests: list[dict[str, Any]] = []

    def __enter__(self):  # noqa: D401
        return self

    def __exit__(self, *exc):  # noqa: D401
        return False

    def request(self, method, url, headers=None, content=None):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers or {},
                "content": content,
            }
        )
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.response


def _webhook_with(client: _FakeClient) -> WebhookHandler:
    h = WebhookHandler()
    h.client_factory = lambda timeout=None: client  # type: ignore[assignment]
    return h


def test_webhook_validate_missing_url():
    with pytest.raises(ValidationError):
        WebhookHandler().validate({})


def test_webhook_validate_scheme_required():
    with pytest.raises(ConfigurationError):
        WebhookHandler().validate({"url": "ftp://x"})


def test_webhook_validate_method_allowed():
    WebhookHandler().validate({"url": "https://x", "method": "PATCH"})


def test_webhook_validate_method_rejected():
    with pytest.raises(ConfigurationError):
        WebhookHandler().validate({"url": "https://x", "method": "GET"})


def test_webhook_validate_headers_wrong_type():
    with pytest.raises(ConfigurationError):
        WebhookHandler().validate({"url": "https://x", "headers": "no"})


def test_webhook_validate_header_bad_value():
    with pytest.raises(ConfigurationError):
        WebhookHandler().validate(
            {"url": "https://x", "headers": {"a": {"nested": 1}}}
        )


def test_webhook_validate_timeout_too_high():
    with pytest.raises(ConfigurationError):
        WebhookHandler().validate({"url": "https://x", "timeout": 1000})


def test_webhook_validate_timeout_zero_rejected():
    with pytest.raises(ConfigurationError):
        WebhookHandler().validate({"url": "https://x", "timeout": 0})


def test_webhook_validate_timeout_wrong_type():
    with pytest.raises(ConfigurationError):
        WebhookHandler().validate({"url": "https://x", "timeout": "10"})


def test_webhook_validate_payload_wrong_type():
    with pytest.raises(ConfigurationError):
        WebhookHandler().validate({"url": "https://x", "payload": "no"})


def test_webhook_execute_success_default_payload():
    client = _FakeClient(response=_FakeResp(200, "OK"))
    handler = _webhook_with(client)
    ctx = _make_ctx(db=_DummyDB())
    result = handler.execute(ctx, {"url": "https://example.com/hook"})
    assert result.success and result.output["status"] == 200
    req = client.requests[0]
    assert req["method"] == "POST"
    assert req["headers"]["Content-Type"] == "application/json"
    assert req["headers"]["X-Workflow-Id"] == ctx.workflow_id
    assert b"workflowId" in req["content"]


def test_webhook_execute_custom_payload_and_headers():
    client = _FakeClient()
    handler = _webhook_with(client)
    ctx = _make_ctx(db=_DummyDB())
    handler.execute(
        ctx,
        {
            "url": "https://example.com/hook",
            "method": "PUT",
            "headers": {"X-Custom": "v"},
            "payload": {"hello": "world"},
        },
    )
    req = client.requests[0]
    assert req["method"] == "PUT"
    assert req["headers"]["X-Custom"] == "v"
    assert req["content"] == b'{"hello": "world"}'


def test_webhook_execute_5xx_is_transient():
    client = _FakeClient(response=_FakeResp(503, "unavailable"))
    handler = _webhook_with(client)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        handler.execute(ctx, {"url": "https://example.com"})
    assert excinfo.value.retryable is True


def test_webhook_execute_429_is_transient():
    client = _FakeClient(response=_FakeResp(429, "slow down"))
    handler = _webhook_with(client)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        handler.execute(ctx, {"url": "https://example.com"})
    assert excinfo.value.retryable is True


def test_webhook_execute_4xx_is_business_error():
    client = _FakeClient(response=_FakeResp(404, "not found"))
    handler = _webhook_with(client)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        handler.execute(ctx, {"url": "https://example.com"})
    assert excinfo.value.retryable is False


def test_webhook_execute_timeout_is_transient():
    client = _FakeClient(raise_exc=httpx.ReadTimeout("timed out"))
    handler = _webhook_with(client)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        handler.execute(ctx, {"url": "https://example.com"})
    assert excinfo.value.retryable is True


def test_webhook_execute_transport_error_is_transient():
    client = _FakeClient(raise_exc=httpx.ConnectError("boom"))
    handler = _webhook_with(client)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        handler.execute(ctx, {"url": "https://example.com"})
    assert excinfo.value.retryable is True


def test_webhook_execute_unserializable_payload():
    handler = WebhookHandler()
    handler.client_factory = lambda timeout=None: _FakeClient()  # type: ignore
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError):
        # validate happens first — bypass by passing dict but unusable content
        # via a set (which is not a JSON scalar) inside a dict value.
        handler.execute(
            ctx,
            {"url": "https://example.com", "payload": {"bad": {1, 2}}},
        )


def test_webhook_response_snippet_truncated():
    long_body = "x" * 2000
    client = _FakeClient(response=_FakeResp(200, long_body))
    handler = _webhook_with(client)
    ctx = _make_ctx(db=_DummyDB())
    result = handler.execute(ctx, {"url": "https://x"})
    assert len(result.output["responseSnippet"]) == 500


# =========================================================================== #
# EntityUpdateHandler
# =========================================================================== #


def test_entity_validate_unknown_type():
    with pytest.raises(ConfigurationError):
        EntityUpdateHandler().validate(
            {"entity_type": "spaceship", "operation": "create", "payload": {}}
        )


def test_entity_validate_unknown_operation():
    with pytest.raises(ConfigurationError):
        EntityUpdateHandler().validate(
            {"entity_type": "volunteer", "operation": "annihilate"}
        )


def test_entity_validate_create_requires_payload():
    with pytest.raises(ConfigurationError):
        EntityUpdateHandler().validate(
            {"entity_type": "volunteer", "operation": "create"}
        )


def test_entity_validate_update_requires_id_and_payload():
    with pytest.raises(ConfigurationError):
        EntityUpdateHandler().validate(
            {"entity_type": "volunteer", "operation": "update", "payload": {"x": 1}}
        )
    with pytest.raises(ConfigurationError):
        EntityUpdateHandler().validate(
            {"entity_type": "volunteer", "operation": "update", "entity_id": "v-1"}
        )


def test_entity_validate_status_requires_id_and_status():
    with pytest.raises(ConfigurationError):
        EntityUpdateHandler().validate(
            {"entity_type": "volunteer", "operation": "status", "entity_id": "v-1"}
        )


def test_entity_validate_roles_type():
    with pytest.raises(ConfigurationError):
        EntityUpdateHandler().validate(
            {
                "entity_type": "volunteer",
                "operation": "create",
                "payload": {"x": 1},
                "roles": "admin",
            }
        )


def test_entity_validate_ok_create():
    EntityUpdateHandler().validate(
        {
            "entity_type": "volunteer",
            "operation": "create",
            "payload": {"user_id": "u"},
        }
    )


def test_entity_alias_public_information_maps_to_public_resource(monkeypatch):
    called = {}

    def _fake_create(db, *, roles, created_by, payload):  # noqa: ARG001
        called["hit"] = True
        return SimpleNamespace(id=uuid.uuid4(), status="draft")

    import app.services.public_access as _pub
    monkeypatch.setattr(_pub, "create_public_resource", _fake_create)

    ctx = _make_ctx(db=_DummyDB())
    result = EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "public_information",
            "operation": "create",
            "payload": {"title": "x"},
        },
    )
    assert called["hit"] is True
    assert result.output["entityType"] == "public_resource"


def test_entity_volunteer_create(monkeypatch):
    import app.services.volunteer as _v

    def _fake(db, *, roles, payload):  # noqa: ARG001
        assert "super_admin" in list(roles)
        return SimpleNamespace(id=uuid.uuid4(), status="available")

    monkeypatch.setattr(_v, "create_volunteer", _fake)
    ctx = _make_ctx(db=_DummyDB())
    result = EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "volunteer",
            "operation": "create",
            "payload": {"user_id": "u"},
        },
    )
    assert result.success and result.output["status"] == "available"


def test_entity_volunteer_update(monkeypatch):
    import app.services.volunteer as _v

    def _fake(db, *, roles, volunteer_id, payload):  # noqa: ARG001
        return SimpleNamespace(id=volunteer_id, status="available")

    monkeypatch.setattr(_v, "update_volunteer", _fake)
    ctx = _make_ctx(db=_DummyDB())
    result = EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "volunteer",
            "operation": "update",
            "entity_id": "v-1",
            "payload": {"name": "x"},
        },
    )
    assert result.success


def test_entity_volunteer_status(monkeypatch):
    import app.services.volunteer as _v

    def _fake(db, *, roles, volunteer_id, status):  # noqa: ARG001
        return SimpleNamespace(id=volunteer_id, status=status)

    monkeypatch.setattr(_v, "set_status", _fake)
    ctx = _make_ctx(db=_DummyDB())
    result = EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "volunteer",
            "operation": "status",
            "entity_id": "v-1",
            "status": "inactive",
        },
    )
    assert result.output["status"] == "inactive"


def test_entity_disaster_create(monkeypatch):
    import app.services.disaster as _d

    def _fake(db, *, roles, created_by, payload):  # noqa: ARG001
        return SimpleNamespace(id=uuid.uuid4(), status="reported")

    monkeypatch.setattr(_d, "create_disaster", _fake)
    ctx = _make_ctx(db=_DummyDB(), actor_id=uuid.uuid4())
    result = EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "disaster",
            "operation": "create",
            "payload": {"title": "t", "disaster_type": "flood"},
        },
    )
    assert result.success


def test_entity_disaster_status_maps_to_verifier(monkeypatch):
    import app.services.disaster as _d
    called = {}

    def _verify(db, *, roles, disaster_id):  # noqa: ARG001
        called["v"] = disaster_id
        return SimpleNamespace(id=disaster_id, status="verified")

    monkeypatch.setattr(_d, "verify_disaster", _verify)
    ctx = _make_ctx(db=_DummyDB())
    result = EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "disaster",
            "operation": "status",
            "entity_id": "d-1",
            "status": "verified",
        },
    )
    assert called["v"] == "d-1"
    assert result.output["status"] == "verified"


def test_entity_disaster_status_invalid():
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError):
        EntityUpdateHandler().execute(
            ctx,
            {
                "entity_type": "disaster",
                "operation": "status",
                "entity_id": "d-1",
                "status": "invented",
            },
        )


def test_entity_public_publish(monkeypatch):
    import app.services.public_access as _p
    called = {}

    def _publish(db, *, roles, resource_id):  # noqa: ARG001
        called["id"] = resource_id
        return SimpleNamespace(id=resource_id, status="published")

    monkeypatch.setattr(_p, "publish_public_resource", _publish)
    ctx = _make_ctx(db=_DummyDB())
    result = EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "public_resource",
            "operation": "status",
            "entity_id": "r-1",
            "status": "publish",
        },
    )
    assert called["id"] == "r-1"
    assert result.success


def test_entity_public_update(monkeypatch):
    import app.services.public_access as _p

    def _upd(db, *, roles, resource_id, payload):  # noqa: ARG001
        return SimpleNamespace(id=resource_id, status="draft")

    monkeypatch.setattr(_p, "update_public_resource", _upd)
    ctx = _make_ctx(db=_DummyDB())
    result = EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "public",
            "operation": "update",
            "entity_id": "r-1",
            "payload": {"title": "x"},
        },
    )
    assert result.success


def test_entity_service_validation_error_propagates(monkeypatch):
    import app.services.volunteer as _v

    def _boom(db, *, roles, payload):  # noqa: ARG001
        raise ValidationError("userId is required")

    monkeypatch.setattr(_v, "create_volunteer", _boom)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        EntityUpdateHandler().execute(
            ctx,
            {
                "entity_type": "volunteer",
                "operation": "create",
                "payload": {},
            },
        )
    assert excinfo.value.retryable is False


def test_entity_service_not_found_propagates(monkeypatch):
    import app.services.volunteer as _v

    def _boom(db, *, roles, volunteer_id, payload):  # noqa: ARG001
        raise NotFoundError("Volunteer not found")

    monkeypatch.setattr(_v, "update_volunteer", _boom)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        EntityUpdateHandler().execute(
            ctx,
            {
                "entity_type": "volunteer",
                "operation": "update",
                "entity_id": "x",
                "payload": {"a": 1},
            },
        )
    assert excinfo.value.retryable is False


def test_entity_service_conflict_propagates(monkeypatch):
    import app.services.volunteer as _v

    def _boom(db, *, roles, payload):  # noqa: ARG001
        raise ConflictError("dup")

    monkeypatch.setattr(_v, "create_volunteer", _boom)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError):
        EntityUpdateHandler().execute(
            ctx,
            {
                "entity_type": "volunteer",
                "operation": "create",
                "payload": {"user_id": "u"},
            },
        )


def test_entity_unknown_service_exception_wraps_as_business(monkeypatch):
    import app.services.volunteer as _v

    def _boom(db, *, roles, payload):  # noqa: ARG001
        raise RuntimeError("disk full")

    monkeypatch.setattr(_v, "create_volunteer", _boom)
    ctx = _make_ctx(db=_DummyDB())
    with pytest.raises(ActionExecutionError) as excinfo:
        EntityUpdateHandler().execute(
            ctx,
            {
                "entity_type": "volunteer",
                "operation": "create",
                "payload": {"user_id": "u"},
            },
        )
    assert excinfo.value.retryable is False


def test_entity_custom_roles_forwarded(monkeypatch):
    import app.services.volunteer as _v
    seen: dict[str, list[str]] = {}

    def _fake(db, *, roles, payload):  # noqa: ARG001
        seen["roles"] = list(roles)
        return SimpleNamespace(id=uuid.uuid4(), status="available")

    monkeypatch.setattr(_v, "create_volunteer", _fake)
    ctx = _make_ctx(db=_DummyDB())
    EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "volunteer",
            "operation": "create",
            "payload": {"user_id": "u"},
            "roles": ["ops_manager"],
        },
    )
    assert seen["roles"] == ["ops_manager"]


def test_entity_attribute_alias_same_as_update(monkeypatch):
    import app.services.volunteer as _v
    called: dict[str, Any] = {}

    def _fake(db, *, roles, volunteer_id, payload):  # noqa: ARG001
        called["payload"] = payload
        return SimpleNamespace(id=volunteer_id, status="available")

    monkeypatch.setattr(_v, "update_volunteer", _fake)
    ctx = _make_ctx(db=_DummyDB())
    EntityUpdateHandler().execute(
        ctx,
        {
            "entity_type": "volunteer",
            "operation": "attribute",
            "entity_id": "v-1",
            "payload": {"skills": ["first-aid"]},
        },
    )
    assert called["payload"] == {"skills": ["first-aid"]}


# =========================================================================== #
# Structured logging / result output
# =========================================================================== #


def test_execute_result_output_carries_handler_name(notif_stub):
    ctx = _make_ctx(db=_DummyDB())
    result = NotificationHandler().execute(
        ctx, {"title": "t", "message": "m", "user_id": "u"}
    )
    assert result.output["handler"] == "NotificationHandler"


def test_dry_run_output_labels_reason():
    ctx = _make_ctx(dry_run=True, db=_DummyDB())
    result = WebhookHandler().execute(ctx, {"url": "https://x"})
    assert result.output["reason"] == "dry_run"


def test_context_dry_run_property_reflects_metadata():
    ctx = _make_ctx(dry_run=True)
    assert ctx.dry_run is True
    ctx2 = _make_ctx()
    assert ctx2.dry_run is False