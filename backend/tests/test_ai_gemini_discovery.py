"""Gemini ListModels discovery and fallback regression tests."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

import httpx

from app.services.ai_providers import (
    ChatMessage,
    DEFAULT_GEMINI_MODEL,
    GEMINI_MODEL_PREFERENCE,
    GeminiProvider,
    build_provider,
)


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str | None = None):
        self._payload = payload
        self.status_code = status_code
        self.text = text if text is not None else json.dumps(payload)

    def json(self):
        return self._payload


def _run(coro):
    return asyncio.run(coro)


def _models(*names: str) -> dict:
    return {
        "models": [
            {"name": f"models/{name}", "supportedGenerationMethods": ["generateContent"]}
            for name in names
        ]
    }


def test_list_models_selects_highest_priority_supported_model():
    GeminiProvider.clear_model_cache()

    def _get(self, url, params=None):  # noqa: ARG001
        assert str(url) == "https://generativelanguage.googleapis.com/v1beta/models"
        assert params == {"key": "fake"}
        return _MockResponse(_models("gemini-3.1-flash-lite", "gemini-pro-latest", "gemini-2.5-flash"))

    with patch.object(httpx.Client, "get", new=_get):
        provider = build_provider(provider="gemini", api_key="fake", model="gemini-2.5-flash")

    assert provider.model == "gemini-3.1-flash-lite"
    assert provider.model in GEMINI_MODEL_PREFERENCE


def test_list_models_skips_non_generate_content_and_deprecated_models():
    GeminiProvider.clear_model_cache()
    payload = {
        "models": [
            {"name": "models/gemini-2.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-flash-latest", "supportedGenerationMethods": ["countTokens"]},
            {"name": "models/gemini-pro-latest", "supportedGenerationMethods": ["generateContent"]},
        ]
    }

    assert GeminiProvider._extract_supported_models(payload) == ["gemini-pro-latest"]


def test_list_models_result_is_cached_per_api_key():
    GeminiProvider.clear_model_cache()
    calls = {"get": 0}

    def _get(self, url, params=None):  # noqa: ARG001
        calls["get"] += 1
        return _MockResponse(_models(DEFAULT_GEMINI_MODEL))

    with patch.object(httpx.Client, "get", new=_get):
        assert GeminiProvider.resolve_model(api_key="fake", requested_model="gemini-2.5-flash-lite") == DEFAULT_GEMINI_MODEL
        assert GeminiProvider.resolve_model(api_key="fake", requested_model="gemini-2.5-flash-lite") == DEFAULT_GEMINI_MODEL

    assert calls["get"] == 1


def test_404_retries_once_with_next_supported_model():
    GeminiProvider.clear_model_cache()
    GeminiProvider._store_supported_models("fake", ["gemini-flash-latest", "gemini-3.5-flash"])
    attempted: list[str] = []

    async def _send(self, request):  # noqa: ARG001
        attempted.append(request.url.path)
        if len(attempted) == 1:
            return _MockResponse({}, status_code=404, text='{"error":{"code":404,"message":"not found"}}')
        return _MockResponse({
            "candidates": [{"content": {"parts": [{"text": "ok"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"totalTokenCount": 2},
        })

    provider = GeminiProvider(api_key="fake", model="gemini-flash-latest")
    with patch.object(httpx.AsyncClient, "send", new=_send):
        result = _run(provider.complete([ChatMessage(role="user", content="hi")]))

    assert attempted == [
        "/v1beta/models/gemini-flash-latest:generateContent",
        "/v1beta/models/gemini-3.5-flash:generateContent",
    ]
    assert result.content == "ok"
    assert result.model == "gemini-3.5-flash"