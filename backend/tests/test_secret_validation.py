from __future__ import annotations

from app.core.config import Settings
from app.security.startup import validate_secrets_at_startup


def _mk(**over) -> Settings:
    return Settings(_env_file=None, **over)


def test_default_secret_flagged_as_known_default():
    s = _mk(APP_SECRET_KEY="dev-secret-change-me" + "x" * 16, APP_ENV="development")
    # 32+ chars but a known-default prefix — currently our list checks exact
    # match; ensure the equality entry works separately.
    warns = _mk(APP_SECRET_KEY="dev-secret-change-me").validate_production()
    assert any("known default" in w for w in warns)


def test_short_secret_flagged():
    warns = _mk(APP_SECRET_KEY="a" * 20).validate_production()
    assert any("shorter than 32" in w for w in warns)


def test_strong_secret_in_dev_no_warn():
    s = _mk(APP_SECRET_KEY="a" * 40, APP_ENV="development")
    assert s.validate_production() == []


def test_production_requires_rotation():
    warns = _mk(APP_ENV="production",
                APP_SECRET_KEY="dev-secret-change-me").validate_production()
    assert any("must be rotated" in w for w in warns)


def test_production_debug_flagged():
    warns = _mk(APP_ENV="production", APP_DEBUG=True,
                APP_SECRET_KEY="a" * 64).validate_production()
    assert any("APP_DEBUG" in w for w in warns)


def test_production_sqlite_flagged():
    warns = _mk(APP_ENV="production", APP_SECRET_KEY="a" * 64,
                DATABASE_URL="sqlite:///./db").validate_production()
    assert any("PostgreSQL" in w for w in warns)


def test_production_missing_webhook_secret_flagged():
    warns = _mk(APP_ENV="production", APP_SECRET_KEY="a" * 64,
                WEBHOOK_SIGNING_SECRET="").validate_production()
    assert any("WEBHOOK_SIGNING_SECRET" in w for w in warns)


def test_production_webhook_secret_set_no_warn_for_webhook():
    warns = _mk(APP_ENV="production", APP_SECRET_KEY="a" * 64,
                WEBHOOK_SIGNING_SECRET="s3cret",
                SECURITY_CSP_ENFORCE=True).validate_production()
    assert not any("WEBHOOK_SIGNING_SECRET" in w for w in warns)


def test_production_csp_reportonly_flagged():
    warns = _mk(APP_ENV="production", APP_SECRET_KEY="a" * 64,
                WEBHOOK_SIGNING_SECRET="x",
                SECURITY_CSP_ENFORCE=False).validate_production()
    assert any("CSP" in w for w in warns)


def test_test_secret_flagged_as_known_default():
    warns = _mk(APP_SECRET_KEY="test-secret-that-is-long-enough").validate_production()
    assert any("known default" in w for w in warns)


def test_validate_at_startup_runs_and_returns_list():
    got = validate_secrets_at_startup()
    assert isinstance(got, list)
