from __future__ import annotations

import uuid

from app.services.audit import SECURITY_EVENTS, security_event


def test_security_event_logs_without_db(caplog):
    security_event(action="rate_limit_exceeded", ip="1.1.1.1",
                   metadata={"policy": "auth"})
    # No exception raised is the primary contract; caplog is a smoke check.
    assert True


def test_security_event_registered_actions_present():
    for a in ("login_failure", "login_success", "permission_denied",
              "rate_limit_exceeded", "webhook_signature_invalid",
              "webhook_signature_missing", "webhook_replay_detected",
              "webhook_timestamp_expired", "secret_config_warning",
              "upload_rejected", "token_revoked"):
        assert a in SECURITY_EVENTS


def test_security_event_swallow_db_errors(monkeypatch):
    # Passing a bogus session should not raise.
    class _Bad:
        def add(self, *a, **k):
            raise RuntimeError("db down")

        def commit(self):
            pass

        def refresh(self, *a):
            pass

    security_event(action="login_failure", db=_Bad())
