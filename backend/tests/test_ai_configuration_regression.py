"""Regression: deprecated Gemini model ids must never reach the provider.

These tests protect the model-resolution chain:

    WorkspaceAiSettings.model / settings.GEMINI_MODEL
        -> build_provider(provider="gemini", model=...)
            -> GeminiProvider(model=<resolved>)

A fresh install (no workspace override, .env default) or a stale workspace
row saved with the deprecated ``gemini-2.5-flash`` id must both resolve to
the platform default from ``settings.GEMINI_MODEL``.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.services import ai_providers
from app.services.ai_providers import (
    DEPRECATED_GEMINI_MODELS,
    DEFAULT_GEMINI_MODEL,
    GEMINI_MODEL_PREFERENCE,
    GeminiProvider,
    _coerce_gemini_model,
    build_provider,
)


DEPRECATED = "gemini-2.5-flash"


def test_settings_default_is_not_deprecated():
    """The Settings default must be a currently-supported model id."""
    assert settings.GEMINI_MODEL not in DEPRECATED_GEMINI_MODELS
    assert settings.GEMINI_MODEL != DEPRECATED
    assert settings.GEMINI_MODEL == DEFAULT_GEMINI_MODEL
    assert "gemini-2.5-flash-lite" not in GEMINI_MODEL_PREFERENCE


def test_fresh_install_resolves_to_configured_default(monkeypatch):
    """No workspace override + empty model -> highest discovered default wins."""
    monkeypatch.setattr(GeminiProvider, "discover_supported_models_sync", lambda _key: [DEFAULT_GEMINI_MODEL])
    prov = build_provider(provider="gemini", api_key="k", model="")
    assert isinstance(prov, GeminiProvider)
    assert prov.model == settings.GEMINI_MODEL
    assert prov.model != DEPRECATED


def test_stale_workspace_model_is_coerced(monkeypatch):
    """Deprecated workspace override must be replaced with the platform default."""
    monkeypatch.setattr(GeminiProvider, "discover_supported_models_sync", lambda _key: [DEFAULT_GEMINI_MODEL])
    prov = build_provider(provider="gemini", api_key="k", model=DEPRECATED)
    assert prov.model == settings.GEMINI_MODEL
    assert prov.model != DEPRECATED


@pytest.mark.parametrize("stale", sorted(DEPRECATED_GEMINI_MODELS))
def test_all_known_deprecated_ids_are_coerced(stale: str):
    assert _coerce_gemini_model(stale) == settings.GEMINI_MODEL


def test_supported_workspace_model_is_preserved():
    """A caller-specified non-deprecated model must pass through untouched."""
    prov = build_provider(provider="gemini", api_key="k", model="gemini-2.5-pro")
    assert prov.model == "gemini-2.5-pro"


def test_load_settings_strips_deprecated_model(monkeypatch):
    """API `_load_settings` should return an empty model for stale rows."""
    from app.api.v1 import ai as ai_api

    class _Row:
        provider = "gemini"
        model = DEPRECATED
        api_key_ciphertext = ""
        base_url = ""
        project_id = ""
        temperature = 0.4
        max_tokens = 1024

    class _Query:
        def filter(self, *_a, **_k):
            return self

        def one_or_none(self):
            return _Row()

    class _DB:
        def query(self, *_a, **_k):
            return _Query()

    import uuid

    out = ai_api._load_settings(_DB(), uuid.uuid4())
    assert out["provider"] == "gemini"
    assert out["model"] == ""  # coerced -> downstream falls back to Settings.GEMINI_MODEL


def test_bootstrap_provider_never_uses_deprecated_default(monkeypatch):
    """The globally-registered Gemini provider must not carry a deprecated id."""
    monkeypatch.setattr(ai_providers, "_providers", {}, raising=False)
    monkeypatch.setattr(ai_providers, "_bootstrapped", False, raising=False)
    monkeypatch.setattr(ai_providers.settings, "GEMINI_API_KEY", "fake-key", raising=False)
    monkeypatch.setattr(GeminiProvider, "discover_supported_models_sync", lambda _key: [DEFAULT_GEMINI_MODEL])
    ai_providers._bootstrap()
    prov = ai_providers._providers.get("gemini")
    assert prov is not None
    assert prov.model not in DEPRECATED_GEMINI_MODELS