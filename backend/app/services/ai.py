"""AI service.

Domain-oriented facade over a pluggable :mod:`ai_providers` layer.

Handles: content generation for every campaign kind, review passes
(compliance/tone/readability/inclusive language), rewrite/expand/shorten,
subject/headline/summary, sentiment, streaming, prompt-template rendering
with variables, prompt-injection filtering, in-process cache, and usage
metering hooked into :class:`AIHistory`.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from typing import Any, AsyncIterator

from app.core.config import settings
from app.core.exceptions import DomainError, RateLimitError, ValidationError
from app.services.ai_providers import (
    ChatMessage,
    build_provider,
    get_provider,
    SUPPORTED_PROVIDERS,
)


# ------------------------------------------------------------------ prompts
SYSTEM_PROMPTS: dict[str, str] = {
    "generate": "You are an enterprise communications assistant. Draft clear, culturally sensitive, on-brand content.",

    "translate": (
        "You are a professional multilingual translator. "
        "Translate the text accurately while preserving meaning, tone, formatting, "
        "bullet lists, links, placeholders, and named entities. "
        "Return ONLY the translated text. "
        "Do not explain. Do not summarize. Do not add notes."
    ),

    "rewrite": "Rewrite the following content preserving intent, improving clarity and concision.",
    "expand": "Expand the following draft with supporting detail without changing its meaning.",
    "shorten": "Shorten the following content by at least 40% while preserving the essential message.",
    "summarize": "Summarize the following content in three sentences or fewer.",
    "improve": "Improve grammar, tone, and readability while preserving voice.",
    "grammar": "Correct grammar and spelling. Return only the corrected content.",
    "tone": "Adjust the tone of the content per the user's requested tone. Preserve facts.",
    "subject": "Return only a single compelling subject line, plain text, no quotes.",
    "headline": "Return only a single strong headline, plain text, no quotes.",
    "simplify": "Rewrite the content at a 6th-grade reading level. Preserve facts and calls-to-action.",

    "compliance": (
        "You are a compliance reviewer. Return strictly a JSON object: "
        '{"risk":"low|medium|high","issues":[{"category":str,"severity":"low|medium|high","message":str}],"suggestions":[str]}'
    ),

    "sentiment": (
        "Analyze sentiment and tone. Return strictly a JSON object: "
        '{"sentiment":"positive|neutral|negative","tone":str,"formality":"formal|neutral|casual","confidence":number}'
    ),

    "readability": (
        "Score readability. Return strictly a JSON object: "
        '{"grade":number,"score":number,"level":"easy|standard|difficult"}'
    ),

    "inclusive": (
        "Flag non-inclusive or exclusionary language. Return strictly a JSON object: "
        '{"issues":[{"phrase":str,"suggestion":str,"reason":str}]}'
    ),

    # Domain-specific presets
    "email": "Draft a professional email. Include a subject line prefixed 'Subject:' followed by a blank line then the body.",
    "sms": "Draft an SMS under 160 characters. No emojis unless requested.",
    "whatsapp": "Draft a WhatsApp message under 320 characters. Warm, direct.",
    "circular": "Draft a formal government circular with clear headings and reference codes.",
    "emergency": "Draft a concise emergency alert. Direct, actionable, no jargon. Under 280 characters.",
    "healthcare": "Draft a healthcare notice using plain language, WHO-compliant tone, actionable steps.",
    "university": "Draft a university notice with formal register, clear dates and actions.",
    "ngo": "Draft NGO awareness content with an inclusive, empowering tone and a clear call-to-action.",

    "press_release": (
        "Draft a press release in inverted-pyramid style: dateline, lede, quote, body, boilerplate."
    ),
}

DOMAIN_MODE_ALIASES = {
    "email_generation": "email",
    "sms_generation": "sms",
    "whatsapp_generation": "whatsapp",
    "government_circular": "circular",
    "emergency_alert": "emergency",
    "healthcare_notice": "healthcare",
    "university_notice": "university",
    "ngo_awareness": "ngo",
    "press_release_generation": "press_release",
}
# ------------------------------------------------------------------ security

_INJECTION_PATTERNS = [
    r"ignore (all|previous|prior) instructions",
    r"disregard (the|your) (system|instructions)",
    r"reveal (the|your) (system prompt|instructions)",
    r"jailbreak",
    r"pretend to be",
]


def sanitize_prompt(prompt: str, *, max_len: int = 8000) -> str:
    if not prompt or not prompt.strip():
        raise ValidationError("Prompt cannot be empty")
    if len(prompt) > max_len:
        raise ValidationError(f"Prompt exceeds {max_len} characters", details={"length": len(prompt)})
    lowered = prompt.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            raise ValidationError("Prompt rejected by safety filter", details={"code": "prompt_injection"})
    return prompt.strip()


# ------------------------------------------------------------------ cache

class _AICache:
    """Simple TTL cache. Redis-backed in production; interface unchanged."""

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 2000) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> dict | None:
        row = self._store.get(key)
        if not row:
            return None
        ts, value = row
        if time.monotonic() - ts > self._ttl:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: dict) -> None:
        if len(self._store) >= self._max:
            # Drop the oldest ~10% of entries.
            for k in list(self._store.keys())[: max(1, self._max // 10)]:
                self._store.pop(k, None)
        self._store[key] = (time.monotonic(), value)


_cache = _AICache()


def _cache_key(mode: str, prompt: str, language: str, tone: str | None) -> str:
    raw = f"{mode}|{language}|{tone or ''}|{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ------------------------------------------------------------------ rate limit

class _RateBucket:
    def __init__(self, per_minute: int) -> None:
        self._per_minute = per_minute
        self._events: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        now = time.monotonic()
        window = [t for t in self._events.get(key, []) if now - t < 60]
        if len(window) >= self._per_minute:
            raise RateLimitError("AI request rate limit exceeded")
        window.append(now)
        self._events[key] = window


_rate = _RateBucket(per_minute=int(getattr(settings, "AI_RATE_LIMIT_PER_MINUTE", 60)))


# ------------------------------------------------------------------ core API


def _system_for(mode: str, *, tone: str | None, language: str) -> str:
    canonical = DOMAIN_MODE_ALIASES.get(mode, mode)
    system = SYSTEM_PROMPTS.get(canonical, SYSTEM_PROMPTS["generate"])
    if tone:
        system += f" Target tone: {tone}."
    if language and language.lower() != "en":
        system += f" Respond in language code: {language}."
    return system


async def generate(
    *,
    prompt: str,
    mode: str = "generate",
    tone: str | None = None,
    language: str = "en",
    provider: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    cache: bool = True,
    rate_limit_key: str | None = None,
    workspace_settings: dict | None = None,
) -> dict[str, Any]:
    safe_prompt = sanitize_prompt(prompt)
    if rate_limit_key:
        _rate.check(rate_limit_key)
    key = _cache_key(mode, safe_prompt, language, tone)
    if cache:
        cached = _cache.get(key)
        if cached is not None:
            return {**cached, "cached": True}

    prov = _resolve_provider(provider=provider, workspace_settings=workspace_settings)
    system = _system_for(mode, tone=tone, language=language)
    default_temp = 0.2 if mode in {"grammar", "compliance", "sentiment", "readability", "inclusive"} else settings.AI_DEFAULT_TEMPERATURE
    if temperature is None and workspace_settings and workspace_settings.get("temperature") is not None:
        default_temp = float(workspace_settings["temperature"])
    temp = temperature if temperature is not None else default_temp
    if max_tokens is None and workspace_settings and workspace_settings.get("max_tokens"):
        max_tokens = int(workspace_settings["max_tokens"])
    started = time.monotonic()
    result = await prov.complete(
        [ChatMessage(role="system", content=system), ChatMessage(role="user", content=safe_prompt)],
        temperature=temp,
        max_tokens=max_tokens,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    payload = {
        "content": result.content,
        "model": result.model,
        "provider": prov.name,
        "tokens": result.total_tokens,
        "promptTokens": result.prompt_tokens,
        "completionTokens": result.completion_tokens,
        "finishReason": result.finish_reason,
        "responseTimeMs": elapsed_ms,
        "cached": False,
    }
    if cache:
        _cache.set(key, payload)
    return payload


def _resolve_provider(*, provider: str | None, workspace_settings: dict | None):
    """Prefer workspace-level override, then explicit param, then global default."""
    if workspace_settings and workspace_settings.get("provider"):
        ws_provider = str(workspace_settings["provider"]).lower()
        if ws_provider in SUPPORTED_PROVIDERS:
            try:
                return build_provider(
                    provider=ws_provider,
                    api_key=workspace_settings.get("api_key") or "",
                    model=workspace_settings.get("model") or "",
                    base_url=workspace_settings.get("base_url") or "",
                    project_id=workspace_settings.get("project_id") or "",
                )
            except DomainError:
                # Fall through to the global default when the workspace-scoped
                # provider is misconfigured. Never surface the secret.
                pass
    return get_provider(provider)


async def stream(*, prompt: str, mode: str = "generate", provider: str | None = None) -> AsyncIterator[str]:
    safe_prompt = sanitize_prompt(prompt)
    prov = get_provider(provider)
    system = _system_for(mode, tone=None, language="en")
    async for chunk in prov.stream(
        [ChatMessage(role="system", content=system), ChatMessage(role="user", content=safe_prompt)],
    ):
        yield chunk


# ------------------------------------------------------------------ review


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()
    # Strip fenced code blocks.
    if text.startswith("```"):
        text = re.sub(r"^```(json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Extract the largest JSON object substring.
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {"raw": text}


async def review(*, content: str, checks: list[str] | None = None, provider: str | None = None) -> dict[str, Any]:
    """Run selected review checks in parallel."""
    checks = checks or ["compliance", "sentiment", "readability", "inclusive"]
    async def _run(mode: str) -> tuple[str, dict]:
        result = await generate(prompt=content, mode=mode, provider=provider, cache=True)
        return mode, _extract_json(result["content"])

    outputs = await asyncio.gather(*[_run(c) for c in checks], return_exceptions=True)
    result: dict[str, Any] = {}
    for entry in outputs:
        if isinstance(entry, Exception):
            continue
        mode, data = entry
        result[mode] = data
    result["qualityScore"] = _compute_quality(result)
    return result


def _compute_quality(result: dict) -> int:
    """Aggregate a 0-100 quality score from review sub-results."""
    score = 100
    risk = (result.get("compliance") or {}).get("risk")
    score -= {"low": 0, "medium": 15, "high": 40}.get(risk, 0)
    if issues := ((result.get("inclusive") or {}).get("issues") or []):
        score -= min(20, 5 * len(issues))
    grade = (result.get("readability") or {}).get("grade")
    if isinstance(grade, (int, float)) and grade > 12:
        score -= 10
    return max(0, min(100, score))


# ------------------------------------------------------------------ prompt render


_VAR_PATTERN = re.compile(r"\{\{\s*([\w.]+)\s*(?:\|\s*default:\s*([^}]+?))?\s*\}\}")


def render_prompt(body: str, variables: dict[str, Any]) -> tuple[str, list[str]]:
    """Substitute `{{var}}` and `{{var|default:fallback}}` placeholders.

    Returns the rendered text plus a list of missing variables (with no default).
    """
    missing: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        path = match.group(1)
        default = (match.group(2) or "").strip()
        value = _lookup(variables, path)
        if value is None or value == "":
            if default:
                return default
            missing.append(path)
            return f"[[{path}]]"
        return str(value)

    return _VAR_PATTERN.sub(_sub, body), missing


def _lookup(source: dict[str, Any], path: str) -> Any:
    cur: Any = source
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def available_providers() -> list[str]:
    from app.services.ai_providers import available_providers as _p
    return _p()
