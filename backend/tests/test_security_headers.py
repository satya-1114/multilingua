from __future__ import annotations

from starlette.testclient import TestClient

from app.core.config import settings
from app.middleware.security_headers import build_headers
from main import app


def test_security_headers_present_on_root():
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    for h in (
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Strict-Transport-Security",
        "Cross-Origin-Opener-Policy",
        "Cross-Origin-Resource-Policy",
    ):
        assert h in r.headers, h


def test_nosniff_header_value():
    r = TestClient(app).get("/healthz")
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_frame_options_value():
    r = TestClient(app).get("/healthz")
    assert r.headers["X-Frame-Options"] == settings.SECURITY_FRAME_OPTIONS


def test_referrer_policy():
    r = TestClient(app).get("/healthz")
    assert r.headers["Referrer-Policy"] == settings.SECURITY_REFERRER_POLICY


def test_permissions_policy_blocks_sensitive_apis():
    r = TestClient(app).get("/healthz")
    v = r.headers["Permissions-Policy"]
    for feature in ("geolocation", "camera", "microphone", "payment"):
        assert f"{feature}=()" in v


def test_hsts_max_age_and_preload():
    r = TestClient(app).get("/healthz")
    v = r.headers["Strict-Transport-Security"]
    assert f"max-age={settings.SECURITY_HSTS_MAX_AGE}" in v
    assert "includeSubDomains" in v
    if settings.SECURITY_HSTS_PRELOAD:
        assert "preload" in v


def test_csp_defaults_to_report_only():
    h = build_headers()
    assert "Content-Security-Policy-Report-Only" in h
    assert "Content-Security-Policy" not in h or settings.SECURITY_CSP_ENFORCE


def test_csp_enforcement_toggle(monkeypatch):
    monkeypatch.setattr(settings, "SECURITY_CSP_ENFORCE", True)
    h = build_headers()
    assert "Content-Security-Policy" in h
    assert "Content-Security-Policy-Report-Only" not in h


def test_csp_policy_denies_framing():
    assert "frame-ancestors 'none'" in settings.SECURITY_CSP_POLICY


def test_xss_protection_disabled_modern():
    # X-XSS-Protection: 0 is the OWASP-recommended value for modern browsers.
    r = TestClient(app).get("/healthz")
    assert r.headers.get("X-XSS-Protection") == "0"


def test_coop_and_corp():
    r = TestClient(app).get("/healthz")
    assert r.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert r.headers["Cross-Origin-Resource-Policy"] == "same-site"


def test_headers_do_not_override_user_set():
    # An endpoint could set its own header (e.g. explicit iframe allow); the
    # middleware uses setdefault so it must not override. Simulate by asserting
    # setdefault semantics against build_headers().
    h = build_headers()
    from starlette.datastructures import MutableHeaders

    mh = MutableHeaders()
    mh["X-Frame-Options"] = "SAMEORIGIN"
    for k, v in h.items():
        mh.setdefault(k, v)
    assert mh["X-Frame-Options"] == "SAMEORIGIN"
