"""Provider selection priority tests.

Verifies the Free-First priority (Gemini -> Ollama -> ...) and guarantees
that Ollama is only ever selected when Gemini is unavailable OR the
workspace has explicitly opted in.
"""
from __future__ import annotations

import pytest

from app.core.exceptions import DomainError
from app.services import ai_providers
from app.services.ai_providers import (
    GeminiProvider,
    OllamaProvider,
    _default_provider_name,
    get_provider,
)


@pytest.fixture(autouse=True)
def _reset_registry(monkeypatch):
    monkeypatch.setattr(ai_providers, "_providers", {}, raising=False)
    monkeypatch.setattr(ai_providers, "_bootstrapped", True, raising=False)
    yield


def _register_gemini():
    p = GeminiProvider(api_key="fake-gemini-key", model="gemini-2.5-flash")
    ai_providers.register_provider(p)
    return p


def _register_ollama():
    p = OllamaProvider(base_url="http://localhost:11434", model="llama3.1")
    ai_providers.register_provider(p)
    return p


def test_default_prefers_gemini_when_registered():
    _register_gemini()
    _register_ollama()
    assert _default_provider_name() == "gemini"
    assert get_provider().name == "gemini"


def test_default_falls_back_to_ollama_when_gemini_absent():
    _register_ollama()
    assert _default_provider_name() == "ollama"
    assert get_provider().name == "ollama"


def test_env_ai_provider_ollama_does_not_shadow_gemini(monkeypatch):
    _register_gemini()
    _register_ollama()
    monkeypatch.setattr(ai_providers.settings, "AI_PROVIDER", "ollama", raising=False)
    assert get_provider().name == "gemini"


def test_env_ai_provider_respected_when_gemini_absent(monkeypatch):
    _register_ollama()
    monkeypatch.setattr(ai_providers.settings, "AI_PROVIDER", "ollama", raising=False)
    assert get_provider().name == "ollama"


def test_explicit_caller_name_always_wins():
    _register_gemini()
    _register_ollama()
    assert get_provider("ollama").name == "ollama"
    assert get_provider("gemini").name == "gemini"


def test_no_providers_raises():
    with pytest.raises(DomainError):
        _default_provider_name()


def test_workspace_explicit_ollama_is_used():
    from app.services import ai as ai_service

    _register_gemini()
    prov = ai_service._resolve_provider(
        provider=None,
        workspace_settings={"provider": "ollama", "base_url": "http://localhost:11434", "model": "llama3.1"},
    )
    assert prov.name == "ollama"


def test_workspace_without_provider_uses_global_gemini():
    from app.services import ai as ai_service

    _register_gemini()
    _register_ollama()
    prov = ai_service._resolve_provider(provider=None, workspace_settings={})
    assert prov.name == "gemini"


def test_workspace_gemini_without_key_falls_through_to_env_gemini():
    from app.services import ai as ai_service

    _register_gemini()
    _register_ollama()
    prov = ai_service._resolve_provider(
        provider=None,
        workspace_settings={"provider": "gemini", "api_key": "", "model": "gemini-2.5-flash"},
    )
    assert prov.name == "gemini"


def test_workspace_gemini_build_failure_does_not_fall_back_to_ollama(monkeypatch):
    from app.services import ai as ai_service

    _register_gemini()
    _register_ollama()

    def _boom(**_kw):
        raise DomainError("gemini misconfigured", details={"code": "provider_disabled"})

    monkeypatch.setattr(ai_service, "build_provider", _boom)
    prov = ai_service._resolve_provider(
        provider=None,
        workspace_settings={"provider": "gemini", "api_key": "x", "model": "gemini-2.5-flash"},
    )
    assert prov.name == "gemini"
