"""AI provider abstraction.

A minimal protocol every provider implements. Callers only depend on
:class:`AIProvider`; swapping between Gemini, Ollama, Hugging Face,
watsonx, or OpenAI is a registration change, not a code change.

Bootstrap priority (free-first):

    1. Google Gemini (free tier — default when GEMINI_API_KEY is set)
    2. Ollama (local — enabled when the daemon is reachable)
    3. Hugging Face Inference API (free tier when HUGGINGFACE_API_KEY set)
    4. IBM watsonx.ai
    5. OpenAI (paid — kept for compatibility, never the default)
    6. Lovable AI Gateway (kept for compatibility)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol

import httpx

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import get_logger

import re as _re

_SECRET_QUERY_RE = _re.compile(r"([?&](?:key|api_key|access_token|token)=)[^&\s'\"]+", _re.IGNORECASE)
_BEARER_RE = _re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")
_SECRET_FIELD_NAMES = {"key", "api_key", "access_token", "token", "authorization"}
log = get_logger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL_PREFERENCE: tuple[str, ...] = (
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-pro-latest",
    "gemini-2.0-flash",
)
DEFAULT_GEMINI_MODEL = GEMINI_MODEL_PREFERENCE[0]

# Gemini model IDs that Google has deprecated for new API keys. When a
# workspace row was saved with one of these — usually from a prior default
# — we must ignore the stored value and fall back to ``settings.GEMINI_MODEL``.
# Do NOT include these in fallback logic inside GeminiProvider itself; this
# gate lives at the resolution boundary so the provider only ever sees a
# supported model id.
DEPRECATED_GEMINI_MODELS: frozenset[str] = frozenset({
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
    "models/gemini-2.5-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-pro",
    "models/gemini-1.5-flash",
    "models/gemini-1.5-pro",
    "models/gemini-1.0-pro",
})


def _is_deprecated_gemini_model(model: str) -> bool:
    return GeminiProvider._normalize_model(model) in {
        GeminiProvider._normalize_model(m) for m in DEPRECATED_GEMINI_MODELS
    }


def _coerce_gemini_model(requested: str) -> str:
    """Return a supported Gemini model id, replacing deprecated ones.

    Falls back to :attr:`Settings.GEMINI_MODEL` when the caller passes an
    empty string or an id known to be deprecated. Logged at ``warning``
    so operators see the coercion in production.
    """
    candidate = (requested or "").strip()
    if not candidate:
        configured = GeminiProvider._normalize_model(settings.GEMINI_MODEL)
        return DEFAULT_GEMINI_MODEL if _is_deprecated_gemini_model(configured) else configured
    if _is_deprecated_gemini_model(candidate):
        log.warning(
            "gemini.model.deprecated",
            extra={
                "requested_model": candidate,
                "resolved_model": DEFAULT_GEMINI_MODEL,
            },
        )
        return DEFAULT_GEMINI_MODEL
    return GeminiProvider._normalize_model(candidate)


def _redact(text: str) -> str:
    """Remove secret material commonly embedded in HTTP error messages.

    Gemini's REST endpoint passes the API key via `?key=...`, and other
    providers surface `Authorization: Bearer ...` headers. Both leak into
    ``httpx``'s default error strings, so scrub them before we let the
    text near a log line, an audit record, or an API response.
    """
    if not text:
        return ""
    text = _SECRET_QUERY_RE.sub(r"\1REDACTED", text)
    text = _BEARER_RE.sub(r"\1REDACTED", text)
    return text


def _redact_http_value(value: Any) -> Any:
    """Redact secrets from structured HTTP diagnostics."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_FIELD_NAMES:
                out[str(key)] = "REDACTED" if item else item
            else:
                out[str(key)] = _redact_http_value(item)
        return out
    if isinstance(value, list):
        return [_redact_http_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_http_value(item) for item in value)
    if isinstance(value, str):
        return _redact(value)
    return value


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class Generation:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str | None = None


class AIProvider(Protocol):
    name: str
    model: str

    async def complete(self, messages: list[ChatMessage], *, temperature: float = 0.4, max_tokens: int | None = None) -> Generation: ...
    async def stream(self, messages: list[ChatMessage], *, temperature: float = 0.4) -> AsyncIterator[str]: ...


# ---------- Helpers -------------------------------------------------------- #


def _messages_to_prompt(messages: list[ChatMessage]) -> str:
    """Flatten a chat transcript for text-completion providers."""
    parts: list[str] = []
    for m in messages:
        prefix = {"system": "System", "user": "User", "assistant": "Assistant"}.get(m.role, m.role.title())
        parts.append(f"{prefix}: {m.content}")
    parts.append("Assistant:")
    return "\n\n".join(parts)


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _wrap_provider_error(name: str, exc: Exception) -> DomainError:
    msg = _redact(str(exc) or exc.__class__.__name__)
    lower = msg.lower()
    code = "provider_error"
    if isinstance(exc, httpx.TimeoutException):
        code = "provider_timeout"
    elif isinstance(exc, httpx.ConnectError):
        code = "provider_unavailable"
    elif "401" in msg or "unauthorized" in lower or "invalid api key" in lower:
        code = "invalid_api_key"
    elif "429" in msg or "rate limit" in lower or "quota" in lower:
        code = "rate_limited"
    elif "404" in msg or "not found" in lower or "was not found" in lower:
        code = "model_not_found"
    elif "400" in msg or "invalid" in lower:
        code = "invalid_request"
    return DomainError(f"AI provider '{name}' failed: {msg}", details={"code": code, "provider": name})


# ---------- OpenAI --------------------------------------------------------- #


class OpenAIProvider:
    name = "openai"

    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        from openai import AsyncOpenAI

        if not api_key:
            raise DomainError("OpenAI provider requires an API key", details={"code": "provider_disabled"})
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=api_key)

    async def complete(self, messages: list[ChatMessage], *, temperature: float = 0.4, max_tokens: int | None = None) -> Generation:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        try:
            response = await self._client.chat.completions.create(**payload)
        except Exception as exc:  # pragma: no cover - network
            raise _wrap_provider_error(self.name, exc) from exc
        choice = response.choices[0]
        usage = response.usage
        return Generation(
            content=choice.message.content or "",
            model=response.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            finish_reason=choice.finish_reason,
        )

    async def stream(self, messages: list[ChatMessage], *, temperature: float = 0.4) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ---------- Lovable AI Gateway (OpenAI-compatible) ------------------------- #


class LovableGatewayProvider(OpenAIProvider):
    """Uses the Lovable AI Gateway via its OpenAI-compatible endpoint."""
    name = "lovable"

    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__(api_key=api_key, model=model, base_url="https://ai.gateway.lovable.dev/v1")


# ---------- Google Gemini -------------------------------------------------- #


class GeminiProvider:
    """Google Gemini via the REST API. Free tier available."""

    name = "gemini"
    _model_cache: dict[str, list[str]] = {}

    def __init__(self, *, api_key: str, model: str) -> None:
        if not api_key:
            raise DomainError("Gemini provider requires an API key", details={"code": "provider_disabled"})
        self.model = self._normalize_model(model)
        self._api_key = api_key
        self._base = GEMINI_API_BASE

    @staticmethod
    def _normalize_model(model: str) -> str:
        """Sanitize a Gemini model identifier.

        Accepts any of the forms a user might paste:
            "gemini-2.5-flash"
            " gemini-2.5-flash\n"       (env stray whitespace)
            "models/gemini-2.5-flash"   (copied from ListModels response)
            "'gemini-2.5-flash'"        (quoted .env value)
        and returns the bare id (e.g. ``gemini-2.5-flash``). The REST path
        already includes ``/models/``; a duplicated prefix produces a 404.
        """
        m = (model or "").strip().strip("'\"")
        if m.lower().startswith("models/"):
            m = m.split("/", 1)[1]
        return m

    @staticmethod
    def _cache_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    @classmethod
    def clear_model_cache(cls) -> None:
        cls._model_cache.clear()

    @classmethod
    def _extract_supported_models(cls, payload: dict[str, Any]) -> list[str]:
        supported: list[str] = []
        for row in payload.get("models") or []:
            if not isinstance(row, dict):
                continue
            methods = set(row.get("supportedGenerationMethods") or [])
            if "generateContent" not in methods:
                continue
            model = cls._normalize_model(str(row.get("name") or ""))
            if model and not _is_deprecated_gemini_model(model) and model not in supported:
                supported.append(model)
        return supported

    @classmethod
    def _cached_supported_models(cls, api_key: str) -> list[str]:
        return list(cls._model_cache.get(cls._cache_key(api_key), []))

    @classmethod
    def _has_cached_supported_models(cls, api_key: str) -> bool:
        return cls._cache_key(api_key) in cls._model_cache

    @classmethod
    def _store_supported_models(cls, api_key: str, models: list[str]) -> list[str]:
        cleaned: list[str] = []
        for model in models:
            normalized = cls._normalize_model(model)
            if normalized and not _is_deprecated_gemini_model(normalized) and normalized not in cleaned:
                cleaned.append(normalized)
        cls._model_cache[cls._cache_key(api_key)] = cleaned
        return cleaned

    @classmethod
    def _preferred_from_supported(cls, supported_models: list[str], *, exclude: str = "") -> str | None:
        supported = {cls._normalize_model(m) for m in supported_models if m}
        excluded = cls._normalize_model(exclude)
        for model in GEMINI_MODEL_PREFERENCE:
            if model in supported and model != excluded:
                return model
        for model in supported_models:
            normalized = cls._normalize_model(model)
            if normalized and normalized != excluded and not _is_deprecated_gemini_model(normalized):
                return normalized
        return None

    @classmethod
    def _fallback_from_supported(cls, supported_models: list[str], *, failed_model: str) -> str | None:
        failed = cls._normalize_model(failed_model)
        preferred = [m for m in GEMINI_MODEL_PREFERENCE if m in {cls._normalize_model(s) for s in supported_models}]
        if failed in preferred:
            for model in preferred[preferred.index(failed) + 1:]:
                return model
        return cls._preferred_from_supported(supported_models, exclude=failed)

    @classmethod
    def discover_supported_models_sync(cls, api_key: str) -> list[str]:
        if cls._has_cached_supported_models(api_key):
            return cls._cached_supported_models(api_key)
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(f"{GEMINI_API_BASE}/models", params={"key": api_key})
            if response.status_code >= 400:
                log.warning(
                    "gemini.models.list_failed",
                    status_code=response.status_code,
                    response_body=_redact(response.text),
                )
                return []
            return cls._store_supported_models(api_key, cls._extract_supported_models(response.json()))
        except Exception as exc:  # pragma: no cover - network resilience
            log.warning("gemini.models.list_failed", error=_redact(str(exc)))
            return []

    @classmethod
    async def discover_supported_models(cls, api_key: str) -> list[str]:
        if cls._has_cached_supported_models(api_key):
            return cls._cached_supported_models(api_key)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{GEMINI_API_BASE}/models", params={"key": api_key})
            if response.status_code >= 400:
                log.warning(
                    "gemini.models.list_failed",
                    status_code=response.status_code,
                    response_body=_redact(response.text),
                )
                return []
            return cls._store_supported_models(api_key, cls._extract_supported_models(response.json()))
        except Exception as exc:  # pragma: no cover - network resilience
            log.warning("gemini.models.list_failed", error=_redact(str(exc)))
            return []

    @classmethod
    def resolve_model(cls, *, api_key: str, requested_model: str = "") -> str:
        requested = cls._normalize_model(requested_model)
        supported = cls.discover_supported_models_sync(api_key)
        if requested and not _is_deprecated_gemini_model(requested):
            if not supported or requested in {cls._normalize_model(m) for m in supported}:
                return requested
        preferred = cls._preferred_from_supported(supported)
        if preferred:
            return preferred
        configured = cls._normalize_model(settings.GEMINI_MODEL)
        if configured and not _is_deprecated_gemini_model(configured):
            return configured
        return DEFAULT_GEMINI_MODEL

    def _payload(self, messages: list[ChatMessage], temperature: float, max_tokens: int | None) -> dict[str, Any]:
        system_parts = [m.content for m in messages if m.role == "system"]
        contents = []
        for m in messages:
            if m.role == "system":
                continue
            content: dict[str, Any] = {"parts": [{"text": m.content}]}
            if m.role == "assistant":
                # Google's Content.role supports "user" and "model". Omit
                # the role for normal user turns so a single text request
                # matches the official REST example exactly.
                content["role"] = "model"
            contents.append(content)
        body: dict[str, Any] = {
            "contents": contents or [{"parts": [{"text": ""}]}],
            "generationConfig": {"temperature": temperature},
        }
        if max_tokens:
            body["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
        return body

    async def complete(self, messages: list[ChatMessage], *, temperature: float = 0.4, max_tokens: int | None = None) -> Generation:
        data = await self._post_generate(messages, temperature, max_tokens)
        candidates = data.get("candidates") or []
        text = ""
        finish = None
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts)
            finish = candidates[0].get("finishReason")
        usage = data.get("usageMetadata") or {}
        return Generation(
            content=text,
            model=self.model,
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            completion_tokens=int(usage.get("candidatesTokenCount", 0)),
            total_tokens=int(usage.get("totalTokenCount", 0) or (_estimate_tokens(text) + sum(_estimate_tokens(m.content) for m in messages))),
            finish_reason=finish,
        )

    async def _post_generate(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        """POST to Google's ``models/{model}:generateContent`` endpoint.

        If Google returns a 404 for the configured model, retry exactly once
        with the next supported cached ListModels candidate. The request
        format and authentication remain the verified Google REST shape.
        """
        params = {"key": self._api_key}
        headers = {"Content-Type": "application/json"}
        body = self._payload(messages, temperature, max_tokens)
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                attempt_model = self.model
                retried = False
                while True:
                    request = client.build_request(
                        "POST",
                        f"{self._base}/models/{attempt_model}:generateContent",
                        params=params,
                        headers=headers,
                        json=body,
                    )
                    log.info(
                        "gemini.generate.request",
                        resolved_model=attempt_model,
                        method=request.method,
                        url=_redact(str(request.url)),
                        headers=_redact_http_value(dict(request.headers)),
                        params=_redact_http_value(params),
                        json_body=body,
                    )
                    response = await client.send(request)
                    try:
                        response_body = response.text
                    except Exception:
                        response_body = "<unreadable>"
                    log.info(
                        "gemini.generate.response",
                        resolved_model=attempt_model,
                        url=_redact(str(request.url)),
                        status_code=response.status_code,
                        response_body=_redact(response_body),
                    )
                    if response.status_code < 400:
                        self.model = attempt_model
                        return response.json()
                    if response.status_code == 404 and not retried:
                        supported = await self.discover_supported_models(self._api_key)
                        fallback = self._fallback_from_supported(supported, failed_model=attempt_model)
                        if fallback and fallback != attempt_model:
                            log.warning(
                                "gemini.generate.retry_model",
                                failed_model=attempt_model,
                                retry_model=fallback,
                            )
                            attempt_model = fallback
                            retried = True
                            continue
                    raise RuntimeError(
                        f"HTTP {response.status_code} at {_redact(str(request.url))}: {_redact(response_body)}"
                    )
        except DomainError:
            raise
        except Exception as exc:
            raise _wrap_provider_error(self.name, exc) from exc

    async def stream(self, messages: list[ChatMessage], *, temperature: float = 0.4) -> AsyncIterator[str]:
        # Simple non-SSE fallback: emit the whole response as one chunk.
        result = await self.complete(messages, temperature=temperature)
        yield result.content


# ---------- Ollama (local) ------------------------------------------------- #


class OllamaProvider:
    """Local Ollama daemon. Supports Llama, Gemma, Mistral, Phi, etc."""

    name = "ollama"

    def __init__(self, *, base_url: str, model: str) -> None:
        self.model = model
        self._base = base_url.rstrip("/")

    @classmethod
    async def is_available(cls, base_url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                r = await client.get(f"{base_url.rstrip('/')}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def complete(self, messages: list[ChatMessage], *, temperature: float = 0.4, max_tokens: int | None = None) -> Generation:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            body["options"]["num_predict"] = max_tokens
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(f"{self._base}/api/chat", json=body)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            raise _wrap_provider_error(self.name, exc) from exc
        text = (data.get("message") or {}).get("content", "") or data.get("response", "")
        return Generation(
            content=text,
            model=self.model,
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            total_tokens=int(data.get("prompt_eval_count", 0) + data.get("eval_count", 0)) or _estimate_tokens(text),
            finish_reason=data.get("done_reason"),
        )

    async def stream(self, messages: list[ChatMessage], *, temperature: float = 0.4) -> AsyncIterator[str]:
        body = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {"temperature": temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", f"{self._base}/api/chat", json=body) as r:
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        chunk = (payload.get("message") or {}).get("content", "")
                        if chunk:
                            yield chunk
        except Exception as exc:  # pragma: no cover
            raise _wrap_provider_error(self.name, exc) from exc


# ---------- Hugging Face Inference API ------------------------------------- #


class HuggingFaceProvider:
    """Hugging Face free Inference API — text-generation task."""

    name = "huggingface"

    def __init__(self, *, api_key: str, model: str) -> None:
        if not api_key:
            raise DomainError("Hugging Face provider requires an API token", details={"code": "provider_disabled"})
        self.model = model
        self._api_key = api_key
        self._base = "https://api-inference.huggingface.co/models"

    async def complete(self, messages: list[ChatMessage], *, temperature: float = 0.4, max_tokens: int | None = None) -> Generation:
        prompt = _messages_to_prompt(messages)
        body = {
            "inputs": prompt,
            "parameters": {
                "temperature": max(0.01, temperature),
                "max_new_tokens": max_tokens or settings.AI_DEFAULT_MAX_TOKENS,
                "return_full_text": False,
            },
            "options": {"wait_for_model": True},
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(f"{self._base}/{self.model}", json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            raise _wrap_provider_error(self.name, exc) from exc
        text = ""
        if isinstance(data, list) and data:
            first = data[0]
            text = (first or {}).get("generated_text", "") if isinstance(first, dict) else str(first)
        elif isinstance(data, dict):
            text = data.get("generated_text", "") or data.get("summary_text", "")
        prompt_tokens = _estimate_tokens(prompt)
        completion_tokens = _estimate_tokens(text)
        return Generation(
            content=text.strip(),
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            finish_reason="stop",
        )

    async def stream(self, messages: list[ChatMessage], *, temperature: float = 0.4) -> AsyncIterator[str]:
        result = await self.complete(messages, temperature=temperature)
        yield result.content


# ---------- IBM watsonx.ai ------------------------------------------------- #


class WatsonxProvider:
    """IBM watsonx.ai text-generation via the REST API."""

    name = "watsonx"

    def __init__(self, *, api_key: str, project_id: str, url: str, model: str) -> None:
        if not (api_key and project_id):
            raise DomainError("watsonx requires WATSONX_API_KEY and WATSONX_PROJECT_ID", details={"code": "provider_disabled"})
        self.model = model
        self._api_key = api_key
        self._project_id = project_id
        self._url = url.rstrip("/")
        self._token: str | None = None

    async def _iam_token(self) -> str:
        if self._token:
            return self._token
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    "https://iam.cloud.ibm.com/identity/token",
                    data={
                        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                        "apikey": self._api_key,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                r.raise_for_status()
                self._token = r.json()["access_token"]
                return self._token
        except Exception as exc:
            raise _wrap_provider_error(self.name, exc) from exc

    async def complete(self, messages: list[ChatMessage], *, temperature: float = 0.4, max_tokens: int | None = None) -> Generation:
        prompt = _messages_to_prompt(messages)
        token = await self._iam_token()
        body = {
            "model_id": self.model,
            "project_id": self._project_id,
            "input": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens or settings.AI_DEFAULT_MAX_TOKENS,
                "decoding_method": "sample",
            },
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    f"{self._url}/ml/v1/text/generation?version=2024-05-01",
                    json=body,
                    headers=headers,
                )
                r.raise_for_status()
                data = r.json()
        except Exception as exc:
            raise _wrap_provider_error(self.name, exc) from exc
        text = ""
        results = data.get("results") or []
        if results:
            text = results[0].get("generated_text", "")
        prompt_tokens = int((results[0] if results else {}).get("input_token_count", _estimate_tokens(prompt)))
        completion_tokens = int((results[0] if results else {}).get("generated_token_count", _estimate_tokens(text)))
        return Generation(
            content=text.strip(),
            model=self.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            finish_reason=(results[0] if results else {}).get("stop_reason", "stop"),
        )

    async def stream(self, messages: list[ChatMessage], *, temperature: float = 0.4) -> AsyncIterator[str]:
        result = await self.complete(messages, temperature=temperature)
        yield result.content


# ---------- Registry ------------------------------------------------------- #


_providers: dict[str, AIProvider] = {}
_bootstrapped = False


def register_provider(provider: AIProvider) -> None:
    _providers[provider.name] = provider


def get_provider(name: str | None = None) -> AIProvider:
    if not _bootstrapped:
        _bootstrap()
    # Explicit caller-provided name always wins.
    if name:
        resolved = name
    else:
        # Free-First priority: when Gemini is configured (its API key is
        # present and the provider registered successfully at bootstrap),
        # it is ALWAYS the platform default. The ``AI_PROVIDER`` env hint
        # is only consulted when Gemini is unavailable — otherwise a stray
        # ``AI_PROVIDER=ollama`` (or any other value) could shadow the
        # configured Gemini key, which contradicts the documented
        # provider priority (Gemini → Ollama → HF → watsonx → OpenAI).
        if "gemini" in _providers:
            resolved = "gemini"
        else:
            env_pref = getattr(settings, "AI_PROVIDER", "").strip().lower()
            resolved = env_pref or _default_provider_name()
    if resolved not in _providers:
        raise DomainError(
            f"AI provider '{resolved}' is not configured",
            details={"available": list(_providers.keys())},
        )
    return _providers[resolved]


def _default_provider_name() -> str:
    # Free-First order. Gemini is preferred whenever it is registered.
    for name in ("gemini", "ollama", "huggingface", "watsonx", "openai", "lovable"):
        if name in _providers:
            return name
    raise DomainError("No AI provider is configured", details={"code": "ai_disabled"})


def _bootstrap() -> None:
    """Initialise providers from environment. Silent if a key is absent."""
    global _bootstrapped
    _bootstrapped = True
    # 1. Gemini (free tier)
    if getattr(settings, "GEMINI_API_KEY", ""):
        try:
            GeminiProvider.discover_supported_models_sync(settings.GEMINI_API_KEY)
            register_provider(GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model=GeminiProvider.resolve_model(
                    api_key=settings.GEMINI_API_KEY,
                    requested_model=getattr(settings, "GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
                ),
            ))
        except DomainError:
            pass
    # 2. Ollama (local — only if the daemon is reachable)
    if getattr(settings, "OLLAMA_ENABLED", True):
        try:
            reachable = asyncio.get_event_loop().run_until_complete(
                OllamaProvider.is_available(settings.OLLAMA_BASE_URL)
            )
        except RuntimeError:
            # Running loop -> can't sync-probe; register optimistically.
            reachable = True
        except Exception:
            reachable = False
        if reachable:
            try:
                register_provider(OllamaProvider(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL,
                ))
            except DomainError:
                pass
    # 3. Hugging Face
    if getattr(settings, "HUGGINGFACE_API_KEY", ""):
        try:
            register_provider(HuggingFaceProvider(
                api_key=settings.HUGGINGFACE_API_KEY,
                model=settings.HUGGINGFACE_MODEL,
            ))
        except DomainError:
            pass
    # 4. IBM watsonx.ai
    if getattr(settings, "WATSONX_API_KEY", "") and getattr(settings, "WATSONX_PROJECT_ID", ""):
        try:
            register_provider(WatsonxProvider(
                api_key=settings.WATSONX_API_KEY,
                project_id=settings.WATSONX_PROJECT_ID,
                url=settings.WATSONX_URL,
                model=settings.WATSONX_MODEL,
            ))
        except DomainError:
            pass
    # 5. OpenAI (never default)
    if settings.OPENAI_API_KEY:
        try:
            register_provider(OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL))
        except DomainError:
            pass
    # 6. Lovable AI Gateway (kept for compatibility)
    lovable_key = getattr(settings, "LOVABLE_API_KEY", "") or ""
    if lovable_key:
        try:
            register_provider(LovableGatewayProvider(
                api_key=lovable_key,
                model=getattr(settings, "LOVABLE_AI_MODEL", "google/gemini-3-flash-preview"),
            ))
        except DomainError:
            pass


def available_providers() -> list[str]:
    if not _bootstrapped:
        _bootstrap()
    return list(_providers.keys())


def build_provider(
    *,
    provider: str,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
    project_id: str = "",
) -> AIProvider:
    """Construct a one-off provider from workspace-level settings.

    Never registered globally — used per-request when a workspace overrides
    the platform default.
    """
    key = provider.strip().lower()
    if key == "gemini":
        # Diagnostic: log exact resolution sources so operators can audit
        # precedence in production. Never emit the API key itself.
        resolved_api_key = api_key or settings.GEMINI_API_KEY
        requested = (model or settings.GEMINI_MODEL or "").strip()
        if not requested:
            model_source = "gemini preference order"
        elif _is_deprecated_gemini_model(requested):
            model_source = f"configured model (deprecated '{requested}' -> discovered/preferred)"
        elif model:
            model_source = "workspace_settings"
        else:
            model_source = "settings.GEMINI_MODEL (.env / config default)"
        resolved = GeminiProvider.resolve_model(api_key=resolved_api_key, requested_model=requested)
        api_key_source = "workspace_settings" if api_key else "settings.GEMINI_API_KEY (.env)"
        log.info(
            "gemini.provider.build",
            extra={
                "provider": "gemini",
                "requested_model": requested or "",
                "resolved_model": resolved,
                "model_source": model_source,
                "api_key_source": api_key_source,
                "settings_gemini_model": settings.GEMINI_MODEL,
            },
        )
        return GeminiProvider(
            api_key=resolved_api_key,
            model=resolved,
        )
    if key == "ollama":
        return OllamaProvider(base_url=base_url or settings.OLLAMA_BASE_URL, model=model or settings.OLLAMA_MODEL)
    if key == "huggingface":
        return HuggingFaceProvider(api_key=api_key or settings.HUGGINGFACE_API_KEY, model=model or settings.HUGGINGFACE_MODEL)
    if key == "watsonx":
        return WatsonxProvider(
            api_key=api_key or settings.WATSONX_API_KEY,
            project_id=project_id or settings.WATSONX_PROJECT_ID,
            url=base_url or settings.WATSONX_URL,
            model=model or settings.WATSONX_MODEL,
        )
    if key == "openai":
        return OpenAIProvider(api_key=api_key or settings.OPENAI_API_KEY, model=model or settings.OPENAI_MODEL)
    if key == "lovable":
        return LovableGatewayProvider(api_key=api_key or settings.LOVABLE_API_KEY, model=model or settings.LOVABLE_AI_MODEL)
    raise DomainError(f"Unknown AI provider '{provider}'", details={"code": "unknown_provider"})


SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "gemini",
    "ollama",
    "huggingface",
    "watsonx",
    "openai",
    "lovable",
)


async def _noop() -> None:
    """Reserved for interface parity; helps IDEs and tests import cleanly."""
    await asyncio.sleep(0)
