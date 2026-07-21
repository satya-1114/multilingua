from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.runtime.action_handlers.webhook import WebhookHandler
from app.runtime.ha.idempotency import (
    InMemoryIdempotencyStore,
    set_default_idempotency_store,
)


@pytest.fixture(autouse=True)
def _isolate_store():
    original = set_default_idempotency_store(InMemoryIdempotencyStore())
    yield
    set_default_idempotency_store(original)


class _FakeResponse:
    def __init__(self, status: int = 200, text: str = "ok"):
        self.status_code = status
        self.text = text


class _FakeClient:
    def __init__(self, response=None):
        self.calls = 0
        self.response = response or _FakeResponse()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def request(self, method, url, headers=None, content=None):
        self.calls += 1
        self.last = {"method": method, "url": url, "headers": headers, "content": content}
        return self.response


def _ctx(execution_id="ex-1"):
    ctx = MagicMock()
    ctx.workflow_id = "wf"
    ctx.execution_id = execution_id
    ctx.trigger_event = None
    ctx.trigger_payload = {}
    return ctx


def _handler(client):
    h = WebhookHandler()
    h.client_factory = lambda **_: client
    return h


def test_first_request_hits_network():
    client = _FakeClient()
    h = _handler(client)
    out = h.run(_ctx(), {"url": "https://x.example", "idempotencyKey": "k"})
    assert client.calls == 1
    assert out["status"] == 200


def test_duplicate_by_key_suppressed():
    client = _FakeClient()
    h = _handler(client)
    cfg = {"url": "https://x.example", "idempotencyKey": "k"}
    h.run(_ctx(), cfg)
    out = h.run(_ctx(execution_id="ex-2"), cfg)
    assert client.calls == 1
    assert out["duplicateSuppressed"] is True
    assert out["idempotencyKey"] == "k"


def test_different_url_not_suppressed():
    client = _FakeClient()
    h = _handler(client)
    h.run(_ctx(), {"url": "https://a.example", "idempotencyKey": "k"})
    h.run(_ctx(), {"url": "https://b.example", "idempotencyKey": "k"})
    assert client.calls == 2


def test_different_key_not_suppressed():
    client = _FakeClient()
    h = _handler(client)
    h.run(_ctx(), {"url": "https://x.example", "idempotencyKey": "a"})
    h.run(_ctx(), {"url": "https://x.example", "idempotencyKey": "b"})
    assert client.calls == 2


def test_no_execution_id_and_no_key_no_suppression():
    client = _FakeClient()
    h = _handler(client)
    ctx = _ctx(execution_id=None)
    h.run(ctx, {"url": "https://x.example"})
    h.run(ctx, {"url": "https://x.example"})
    assert client.calls == 2


def test_execution_id_used_as_default_key():
    client = _FakeClient()
    h = _handler(client)
    ctx = _ctx(execution_id="ex-42")
    h.run(ctx, {"url": "https://x.example"})
    dup = h.run(ctx, {"url": "https://x.example"})
    assert client.calls == 1
    assert dup["duplicateSuppressed"] is True


def test_idempotency_header_forwarded():
    client = _FakeClient()
    h = _handler(client)
    h.run(_ctx(), {"url": "https://x.example", "idempotencyKey": "abc"})
    assert client.last["headers"]["Idempotency-Key"] == "abc"


def test_snake_case_key_accepted():
    client = _FakeClient()
    h = _handler(client)
    cfg = {"url": "https://x.example", "idempotency_key": "kk"}
    h.run(_ctx(), cfg)
    dup = h.run(_ctx(), cfg)
    assert dup["duplicateSuppressed"] is True


def test_custom_ttl_respected():
    client = _FakeClient()
    h = _handler(client)
    cfg = {"url": "https://x.example", "idempotencyKey": "z", "idempotencyTtl": 0.05}
    h.run(_ctx(), cfg)
    import time
    time.sleep(0.1)
    h.run(_ctx(), cfg)
    assert client.calls == 2


def test_duplicate_result_shape():
    client = _FakeClient()
    h = _handler(client)
    cfg = {"url": "https://x.example", "idempotencyKey": "k"}
    h.run(_ctx(), cfg)
    dup = h.run(_ctx(), cfg)
    assert set(dup) >= {"duplicateSuppressed", "idempotencyKey",
                         "originalStoredAt", "url", "method", "status"}
    assert dup["status"] == 0
