from __future__ import annotations

import time

import pytest

from app.security import webhooks as ws


def _sign_ok(body: bytes, secret: str, ts: int | None = None, nonce: str | None = None):
    return ws.sign(body, secret, timestamp=ts, nonce=nonce)


def test_sign_returns_expected_headers():
    h = _sign_ok(b"{}", "s3cret")
    assert ws.SIGNATURE_HEADER in h
    assert ws.TIMESTAMP_HEADER in h
    assert h[ws.SIGNATURE_HEADER].startswith("v1=")


def test_sign_with_nonce_adds_header():
    h = _sign_ok(b"{}", "s3cret", nonce="n-1")
    assert h[ws.NONCE_HEADER] == "n-1"


def test_sign_empty_secret_raises():
    with pytest.raises(ws.WebhookSecurityError):
        ws.sign(b"{}", "")


def test_verify_accepts_valid_signature():
    body = b'{"a":1}'
    ts = int(time.time())
    h = _sign_ok(body, "s", ts=ts)
    assert ws.verify(body, "s", h[ws.SIGNATURE_HEADER], h[ws.TIMESTAMP_HEADER],
                     tolerance_s=60) is True


def test_verify_rejects_tampered_body():
    body = b'{"a":1}'
    ts = int(time.time())
    h = _sign_ok(body, "s", ts=ts)
    with pytest.raises(ws.InvalidSignature):
        ws.verify(b'{"a":2}', "s", h[ws.SIGNATURE_HEADER], h[ws.TIMESTAMP_HEADER],
                  tolerance_s=60)


def test_verify_rejects_wrong_secret():
    body = b"payload"
    ts = int(time.time())
    h = _sign_ok(body, "s1", ts=ts)
    with pytest.raises(ws.InvalidSignature):
        ws.verify(body, "s2", h[ws.SIGNATURE_HEADER], h[ws.TIMESTAMP_HEADER],
                  tolerance_s=60)


def test_verify_rejects_expired_timestamp():
    body = b"x"
    old = int(time.time()) - 3600
    h = _sign_ok(body, "s", ts=old)
    with pytest.raises(ws.ExpiredTimestamp):
        ws.verify(body, "s", h[ws.SIGNATURE_HEADER], h[ws.TIMESTAMP_HEADER],
                  tolerance_s=60)


def test_verify_rejects_future_timestamp_beyond_tolerance():
    body = b"x"
    future = int(time.time()) + 3600
    h = _sign_ok(body, "s", ts=future)
    with pytest.raises(ws.ExpiredTimestamp):
        ws.verify(body, "s", h[ws.SIGNATURE_HEADER], h[ws.TIMESTAMP_HEADER],
                  tolerance_s=60)


def test_verify_accepts_within_tolerance():
    body = b"x"
    ts = int(time.time()) - 30
    h = _sign_ok(body, "s", ts=ts)
    assert ws.verify(body, "s", h[ws.SIGNATURE_HEADER], h[ws.TIMESTAMP_HEADER],
                     tolerance_s=60)


def test_verify_missing_signature_raises():
    with pytest.raises(ws.MissingSignature):
        ws.verify(b"", "s", None, "0", tolerance_s=60)


def test_verify_missing_timestamp_raises():
    with pytest.raises(ws.MissingSignature):
        ws.verify(b"", "s", "v1=deadbeef", None, tolerance_s=60)


def test_verify_bad_timestamp_format_raises():
    with pytest.raises(ws.InvalidSignature):
        ws.verify(b"", "s", "v1=deadbeef", "not-a-number", tolerance_s=60)


def test_verify_unsupported_scheme_raises():
    body = b"x"
    ts = int(time.time())
    with pytest.raises(ws.InvalidSignature):
        ws.verify(body, "s", "v2=abc", str(ts), tolerance_s=60)


def test_verify_empty_secret_raises():
    with pytest.raises(ws.WebhookSecurityError):
        ws.verify(b"", "", "v1=abc", "0", tolerance_s=60)


def test_replay_cache_first_use_succeeds():
    cache = ws.ReplayCache(ttl_s=60)
    assert cache.remember("n1")


def test_replay_cache_second_use_fails():
    cache = ws.ReplayCache(ttl_s=60)
    cache.remember("n1")
    assert cache.remember("n1") is False


def test_replay_cache_expires_after_ttl():
    cache = ws.ReplayCache(ttl_s=1)
    cache.remember("n1")
    time.sleep(1.05)
    assert cache.remember("n1")


def test_verify_with_replay_cache_blocks_replay():
    body = b"x"
    ts = int(time.time())
    h = _sign_ok(body, "s", ts=ts, nonce="abc")
    cache = ws.ReplayCache(ttl_s=60)
    assert ws.verify(body, "s", h[ws.SIGNATURE_HEADER], h[ws.TIMESTAMP_HEADER],
                     tolerance_s=60, nonce_header="abc", replay_cache=cache)
    with pytest.raises(ws.ReplayedRequest):
        ws.verify(body, "s", h[ws.SIGNATURE_HEADER], h[ws.TIMESTAMP_HEADER],
                  tolerance_s=60, nonce_header="abc", replay_cache=cache)


def test_bare_hex_signature_accepted_as_v1():
    body = b"x"
    ts = int(time.time())
    h = _sign_ok(body, "s", ts=ts)
    hex_only = h[ws.SIGNATURE_HEADER].split("=", 1)[1]
    assert ws.verify(body, "s", hex_only, h[ws.TIMESTAMP_HEADER], tolerance_s=60)


def test_sign_uses_current_time_when_absent(monkeypatch):
    fixed = 1700000000
    monkeypatch.setattr("app.security.webhooks.time.time", lambda: fixed)
    h = ws.sign(b"", "s")
    assert h[ws.TIMESTAMP_HEADER] == str(fixed)
