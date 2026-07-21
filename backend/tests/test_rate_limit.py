from __future__ import annotations

import time

import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.security.rate_limit import (
    InMemoryStore,
    Policy,
    RateLimiter,
    default_limiter,
)


@pytest.fixture(autouse=True)
def _reset_limiter():
    default_limiter.store.reset()
    yield
    default_limiter.store.reset()


def test_in_memory_store_increments():
    s = InMemoryStore()
    c1, r1 = s.hit("k", 60)
    c2, r2 = s.hit("k", 60)
    assert c1 == 1 and c2 == 2
    assert r1 == r2


def test_in_memory_store_resets_after_window():
    s = InMemoryStore()
    s.hit("k", 1)
    time.sleep(1.05)
    c, _ = s.hit("k", 1)
    assert c == 1


def test_in_memory_store_reset_all():
    s = InMemoryStore()
    s.hit("k1", 60)
    s.hit("k2", 60)
    s.reset()
    assert s.snapshot() == {}


def test_in_memory_store_reset_one():
    s = InMemoryStore()
    s.hit("k1", 60)
    s.hit("k2", 60)
    s.reset("k1")
    assert list(s.snapshot().keys()) == ["k2"]


def test_policy_resolution_auth():
    r = RateLimiter()
    assert r.resolve_policy("/api/v1/auth/login").name == "auth"
    assert r.resolve_policy("/api/v1/auth/refresh").name == "auth"


def test_policy_resolution_password_reset():
    r = RateLimiter()
    assert r.resolve_policy("/api/v1/auth/password/reset").name == "password_reset"
    assert r.resolve_policy("/api/v1/auth/password-reset").name == "password_reset"


def test_policy_resolution_public():
    r = RateLimiter()
    assert r.resolve_policy("/api/public/p/foo").name == "public"


def test_policy_resolution_admin():
    r = RateLimiter()
    for p in ("/api/v1/security", "/api/v1/system", "/api/v1/runtime",
              "/api/v1/settings", "/api/v1/workspaces", "/api/v1/organizations"):
        assert r.resolve_policy(p).name == "admin"


def test_policy_resolution_default():
    r = RateLimiter()
    assert r.resolve_policy("/api/v1/volunteers").name == "default"


def test_check_allows_within_limit():
    r = RateLimiter()
    p = Policy("t", limit=3, window_s=60)
    for i in range(3):
        d = r.check("key", p)
        assert d.allowed, i
        assert d.remaining == 3 - (i + 1)


def test_check_blocks_over_limit():
    r = RateLimiter()
    p = Policy("t", limit=2, window_s=60)
    r.check("k", p); r.check("k", p)
    d = r.check("k", p)
    assert not d.allowed
    assert d.retry_after > 0


def test_check_remaining_is_zero_at_limit():
    r = RateLimiter()
    p = Policy("t", limit=1, window_s=60)
    d = r.check("k", p)
    assert d.remaining == 0


def test_check_keys_isolated():
    r = RateLimiter()
    p = Policy("t", limit=1, window_s=60)
    assert r.check("a", p).allowed
    assert r.check("b", p).allowed  # different key not affected


def test_check_policies_isolated():
    r = RateLimiter()
    a = Policy("a", limit=1, window_s=60)
    b = Policy("b", limit=1, window_s=60)
    assert r.check("k", a).allowed
    assert r.check("k", b).allowed  # different policy namespace


def test_middleware_allows_health():
    c = TestClient(app_with_low_limits())
    for _ in range(20):
        r = c.get("/healthz")
        assert r.status_code == 200  # exempt


def test_middleware_emits_headers_on_ok():
    c = TestClient(app_with_low_limits())
    r = c.get("/api/v1/volunteers")
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Remaining" in r.headers
    assert "X-RateLimit-Policy" in r.headers


def test_middleware_returns_429_when_exceeded(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 2)
    default_limiter.policies = default_limiter.policies | {
        "default": Policy("default", 2, 60)
    }
    c = TestClient(app_with_low_limits())
    c.get("/api/v1/volunteers")
    c.get("/api/v1/volunteers")
    r = c.get("/api/v1/volunteers")
    assert r.status_code == 429
    body = r.json()
    assert body["error"]["code"] == "rate_limited"
    assert "Retry-After" in r.headers
    # reset for other tests
    from app.security.rate_limit import _policies
    default_limiter.policies = _policies()


def test_429_has_policy_details(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_AUTH_PER_MINUTE", 1)
    from app.security.rate_limit import _policies
    default_limiter.policies = _policies()
    c = TestClient(app_with_low_limits())
    c.post("/api/v1/auth/login", json={})
    r = c.post("/api/v1/auth/login", json={})
    assert r.status_code == 429
    payload = r.json()["error"]
    assert payload["details"]["policy"] == "auth"
    assert payload["details"]["limit"] == 1
    default_limiter.policies = _policies()


def test_disabled_flag_bypasses_middleware(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 1)
    c = TestClient(app_with_low_limits())
    for _ in range(5):
        assert c.get("/api/v1/volunteers").status_code != 429


def test_forwarded_for_used_as_key(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_TRUST_FORWARDED", True)
    from app.middleware.rate_limit import _client_ip
    from starlette.requests import Request

    scope = {"type": "http", "headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")],
             "client": ("9.9.9.9", 0)}
    req = Request(scope)
    assert _client_ip(req) == "1.2.3.4"


def test_identity_prefers_user_over_ip(monkeypatch):
    from app.middleware.rate_limit import _identity
    from app.security.jwt import create_access_token
    from starlette.requests import Request

    token = create_access_token("user-xyz")
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "client": ("1.1.1.1", 0),
    }
    assert _identity(Request(scope)) == "user:user-xyz"


def test_identity_falls_back_to_ip():
    from app.middleware.rate_limit import _identity
    from starlette.requests import Request

    scope = {"type": "http", "headers": [], "client": ("2.2.2.2", 0)}
    assert _identity(Request(scope)).startswith("ip:")


# ---------------------------------------------------------------------- #
# helper — a fresh app instance keeps the module-scoped app clean
# ---------------------------------------------------------------------- #
def app_with_low_limits():
    from main import app as _app
    return _app
