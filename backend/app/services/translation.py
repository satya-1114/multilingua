"""Translation engine.

Features:
- IndicTrans2 backend when `TRANSLATION_BACKEND=indictrans2` and the model
  loads (loaded lazily; falls back to AI provider on failure)
- AI-provider fallback (default) that uses the pluggable AI stack
- Language detection with Unicode-range heuristics
- Batch translation with concurrency control
- Deterministic in-process cache
- Glossary + terminology enforcement
- Translation quality/confidence scoring
- Compare-translation helper
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Any, Iterable

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.services.ai import generate as ai_generate

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil",
    "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi", "gu": "Gujarati",
    "pa": "Punjabi", "or": "Odia", "bn": "Bengali", "ur": "Urdu",
    "as": "Assamese",
}
SUPPORTED_LANGUAGES: frozenset[str] = frozenset(LANGUAGE_NAMES.keys())


_UNICODE_RANGES: list[tuple[str, tuple[int, int]]] = [
    ("hi", (0x0900, 0x097F)),  # Devanagari
    ("bn", (0x0980, 0x09FF)),
    ("pa", (0x0A00, 0x0A7F)),  # Gurmukhi
    ("gu", (0x0A80, 0x0AFF)),
    ("or", (0x0B00, 0x0B7F)),
    ("ta", (0x0B80, 0x0BFF)),
    ("te", (0x0C00, 0x0C7F)),
    ("kn", (0x0C80, 0x0CFF)),
    ("ml", (0x0D00, 0x0D7F)),
    ("ur", (0x0600, 0x06FF)),  # Arabic script (Urdu heuristic)
]


def detect_language(text: str) -> str:
    if not text:
        return "en"
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for code, (lo, hi) in _UNICODE_RANGES:
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
                break
    if not counts:
        return "en"
    return max(counts.items(), key=lambda kv: kv[1])[0]


# ------------------------------------------------------------------ cache

class _TranslationCache:
    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 5000) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: dict[str, tuple[float, dict]] = {}

    def key(self, *, text: str, source: str, target: str) -> str:
        raw = f"{source}|{target}|{text}"
        return hashlib.sha256(raw.encode()).hexdigest()

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
            for k in list(self._store.keys())[: max(1, self._max // 10)]:
                self._store.pop(k, None)
        self._store[key] = (time.monotonic(), value)


_cache = _TranslationCache()


# ------------------------------------------------------------------ glossary

_glossary: dict[str, dict[str, str]] = {}  # source_term -> {target_lang: replacement}


def register_glossary_term(term: str, translations: dict[str, str]) -> None:
    _glossary.setdefault(term, {}).update(translations)


def apply_glossary(text: str, target_language: str) -> str:
    if not _glossary:
        return text
    result = text
    for term, targets in _glossary.items():
        if target_language in targets:
            result = re.sub(rf"\b{re.escape(term)}\b", targets[target_language], result, flags=re.IGNORECASE)
    return result


# ------------------------------------------------------------------ IndicTrans2 (lazy)

_indictrans2_model = None
_indictrans2_available: bool | None = None


async def _try_indictrans2(text: str, source: str, target: str) -> str | None:
    """Try IndicTrans2 backend. Returns None if unavailable or fails."""
    global _indictrans2_model, _indictrans2_available
    if _indictrans2_available is False:
        return None
    if getattr(settings, "TRANSLATION_BACKEND", "ai").lower() != "indictrans2":
        _indictrans2_available = False
        return None
    if _indictrans2_model is None:
        try:
            # Deferred import — IndicTrans2 is a heavy optional dependency.
            from IndicTransToolkit import IndicProcessor  # type: ignore
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # type: ignore

            model_name = getattr(settings, "INDICTRANS2_MODEL", "ai4bharat/indictrans2-en-indic-1B")
            _indictrans2_model = {
                "tokenizer": AutoTokenizer.from_pretrained(model_name, trust_remote_code=True),
                "model": AutoModelForSeq2SeqLM.from_pretrained(model_name, trust_remote_code=True),
                "processor": IndicProcessor(inference=True),
            }
        except Exception:  # noqa: BLE001
            _indictrans2_available = False
            return None
    try:
        m = _indictrans2_model
        processed = m["processor"].preprocess_batch([text], src_lang=source, tgt_lang=target)
        tokens = m["tokenizer"](processed, return_tensors="pt", padding=True, truncation=True)
        out = m["model"].generate(**tokens, max_length=1024)
        decoded = m["tokenizer"].batch_decode(out, skip_special_tokens=True)
        return m["processor"].postprocess_batch(decoded, lang=target)[0]
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ scoring


def _confidence_score(source_text: str, translated_text: str) -> float:
    if not translated_text.strip():
        return 0.0
    len_ratio = len(translated_text) / max(1, len(source_text))
    penalty = 0.0
    if not 0.4 <= len_ratio <= 3.5:
        penalty += 0.2
    if translated_text == source_text:
        penalty += 0.4
    return round(max(0.0, min(1.0, 0.92 - penalty)), 3)


# ------------------------------------------------------------------ public API


async def translate(
    *,
    text: str,
    target_language: str,
    source_language: str | None = None,
    apply_glossary_terms: bool = True,
    use_cache: bool = True,
) -> dict[str, Any]:
    if not text or not text.strip():
        raise ValidationError("Text cannot be empty")
    if target_language not in SUPPORTED_LANGUAGES:
        raise ValidationError(f"Unsupported target language: {target_language}", details={"supported": sorted(SUPPORTED_LANGUAGES)})
    source = source_language or detect_language(text)

    key = _cache.key(text=text, source=source, target=target_language)
    if use_cache:
        cached = _cache.get(key)
        if cached is not None:
            return {**cached, "cached": True}

    if source == target_language:
        result = {
            "sourceLanguage": source, "targetLanguage": target_language,
            "sourceText": text, "translatedText": text,
            "quality": 1.0, "confidence": 1.0, "provider": "identity", "cached": False,
        }
        _cache.set(key, result)
        return result

    translated = await _try_indictrans2(text, source, target_language)
    provider_used = "indictrans2"
    if translated is None:
        # Fallback: AI provider translation.
        target_name = LANGUAGE_NAMES.get(target_language, target_language)
        source_name = LANGUAGE_NAMES.get(source, source)
        prompt = (
            f"Translate the following {source_name} text into {target_name}. "
            "Preserve tone, formatting, and named entities. Return only the translation.\n\n"
            + text
        )
        ai = await ai_generate(prompt=prompt, mode="translate", tone="neutral", language=target_language, temperature=0.1)
        translated = ai["content"].strip()
        provider_used = ai.get("provider", "ai")

    if apply_glossary_terms:
        translated = apply_glossary(translated, target_language)

    result = {
        "sourceLanguage": source,
        "targetLanguage": target_language,
        "sourceText": text,
        "translatedText": translated,
        "quality": _confidence_score(text, translated),
        "confidence": _confidence_score(text, translated),
        "provider": provider_used,
        "cached": False,
    }
    _cache.set(key, result)
    return result


async def translate_batch(
    *, items: Iterable[str], target_language: str,
    source_language: str | None = None, concurrency: int = 4,
) -> list[dict[str, Any]]:
    items_list = list(items)
    if not items_list:
        return []
    sem = asyncio.Semaphore(max(1, concurrency))

    async def _one(text: str) -> dict[str, Any]:
        async with sem:
            return await translate(text=text, target_language=target_language, source_language=source_language)

    return await asyncio.gather(*[_one(t) for t in items_list])


async def compare(*, text: str, target_language: str, source_language: str | None = None) -> dict[str, Any]:
    """Compare two provider outputs and pick the higher-confidence result."""
    a = await translate(text=text, target_language=target_language, source_language=source_language, use_cache=False)
    # A perturbed second pass — same provider chain, no cache — provides a variance signal.
    b = await translate(text=text + " ", target_language=target_language, source_language=source_language, use_cache=False)
    winner = a if a["confidence"] >= b["confidence"] else b
    return {"candidates": [a, b], "recommended": winner}


def supported_languages() -> list[dict[str, str]]:
    return [{"code": c, "name": n} for c, n in LANGUAGE_NAMES.items()]


# =============================================================================
# Multilingual content platform services (Phase 5.2)
# =============================================================================
#
# The functions above power the legacy AI free-text ``/api/v1/translation``
# endpoint. Everything below implements the per-entity translation platform
# (Phase 5.x) — repositories in ``app.repositories.translation``, models in
# ``app.models.translation``. Kept in the same module so callers can import
# both from a single namespace.

# from __future__ import annotations — already declared at module top.

import hashlib as _hashlib  # noqa: E402
import uuid as _uuid  # noqa: E402
from datetime import datetime as _dt, timezone as _tz  # noqa: E402
from typing import Any as _Any, Iterable as _Iterable  # noqa: E402

from sqlalchemy.orm import Session as _Session  # noqa: E402

from app.constants.translation import (  # noqa: E402
    JOB_STATUSES as _JOB_STATUSES,
    JOB_STATUS_CANCELLED as _JOB_CANCELLED,
    JOB_STATUS_COMPLETED as _JOB_COMPLETED,
    JOB_STATUS_FAILED as _JOB_FAILED,
    JOB_STATUS_PENDING as _JOB_PENDING,
    JOB_STATUS_PROCESSING as _JOB_PROCESSING,
    SUPPORTED_ENTITY_TYPES as _ENTITY_TYPES,
    TRANSLATION_STATUSES as _T_STATUSES,
    TRANSLATION_STATUS_DRAFT as _T_DRAFT,
    TRANSLATION_STATUS_PUBLISHED as _T_PUBLISHED,
    TRANSLATION_STATUS_REVIEWED as _T_REVIEWED,
    TRANSLATION_STATUS_TRANSLATED as _T_TRANSLATED,
)
from app.core.exceptions import (  # noqa: E402
    ConflictError as _ConflictError,
    NotFoundError as _NotFoundError,
    ValidationError as _ValidationError,
)
from app.models.translation import (  # noqa: E402
    Translation as _Translation,
    TranslationJob as _TranslationJob,
    TranslationLocale as _TranslationLocale,
)
from app.repositories.translation import (  # noqa: E402
    translation_jobs as _translation_jobs,
    translation_locales as _translation_locales,
    translations as _translations,
)
from app.security.rbac import require_permission as _require_permission  # noqa: E402
from app.services import translation_events as _events  # noqa: E402


# --- Workflow ---------------------------------------------------------------

# Allowed transitions between translation statuses.
_TRANSLATION_TRANSITIONS: dict[str, set[str]] = {
    _T_DRAFT: {_T_TRANSLATED},
    _T_TRANSLATED: {_T_REVIEWED, _T_DRAFT},
    _T_REVIEWED: {_T_PUBLISHED, _T_DRAFT},
    _T_PUBLISHED: {_T_DRAFT},
}

_JOB_TRANSITIONS: dict[str, set[str]] = {
    _JOB_PENDING: {_JOB_PROCESSING, _JOB_CANCELLED, _JOB_FAILED},
    _JOB_PROCESSING: {_JOB_COMPLETED, _JOB_FAILED, _JOB_CANCELLED},
    _JOB_COMPLETED: set(),
    _JOB_FAILED: {_JOB_PENDING},
    _JOB_CANCELLED: set(),
}


_FIELD_NAME_MAX = 80


def _as_uuid_opt(value: _uuid.UUID | str | None) -> _uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, _uuid.UUID):
        return value
    try:
        return _uuid.UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise _ValidationError(f"Invalid UUID: {value!r}") from exc


def _as_uuid(value: _uuid.UUID | str) -> _uuid.UUID:
    out = _as_uuid_opt(value)
    if out is None:
        raise _ValidationError("UUID is required")
    return out


def _validate_entity_type(entity_type: str) -> None:
    if entity_type not in _ENTITY_TYPES:
        raise _ValidationError(
            f"Invalid entity type: {entity_type}",
            details={"allowed": list(_ENTITY_TYPES)},
        )


def _validate_field_name(field_name: str) -> None:
    if not field_name or not field_name.strip():
        raise _ValidationError("field_name is required")
    if len(field_name) > _FIELD_NAME_MAX:
        raise _ValidationError(
            f"field_name too long (max {_FIELD_NAME_MAX})",
            details={"field_name": field_name},
        )


def _validate_locale_code(locale: str) -> None:
    if not locale or len(locale) < 2 or len(locale) > 20:
        raise _ValidationError("Invalid locale code", details={"locale": locale})


def _ensure_supported_locale(db: _Session, locale: str) -> _TranslationLocale | None:
    """When the locale registry has rows, require the target locale to exist
    and be enabled. When the registry is empty, accept any well-formed code
    so early-stage projects aren't blocked before seed data is loaded.
    """
    _validate_locale_code(locale)
    all_locales = _translation_locales.list_locales(db)
    if not all_locales:
        return None
    row = _translation_locales.get_locale(db, locale)
    if row is None:
        raise _ValidationError(
            f"Locale '{locale}' is not registered",
            details={"locale": locale},
        )
    if not row.enabled:
        raise _ConflictError(
            f"Locale '{locale}' is disabled",
            details={"locale": locale},
        )
    return row


def _get_translation_or_404(
    db: _Session, translation_id: _uuid.UUID | str
) -> _Translation:
    obj = _translations.get_translation(db, _as_uuid(translation_id))
    if obj is None:
        raise _NotFoundError(
            "Translation not found", details={"id": str(translation_id)}
        )
    return obj


def _get_job_or_404(
    db: _Session, job_id: _uuid.UUID | str
) -> _TranslationJob:
    obj = _translation_jobs.get_job(db, _as_uuid(job_id))
    if obj is None:
        raise _NotFoundError(
            "Translation job not found", details={"id": str(job_id)}
        )
    return obj


def _assert_transition(current: str, target: str) -> None:
    if current == target:
        return
    allowed = _TRANSLATION_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise _ConflictError(
            f"Invalid translation transition {current!r} -> {target!r}",
            details={"from": current, "to": target, "allowed": sorted(allowed)},
        )


def _assert_job_transition(current: str, target: str) -> None:
    if current == target:
        return
    allowed = _JOB_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise _ConflictError(
            f"Invalid job transition {current!r} -> {target!r}",
            details={"from": current, "to": target, "allowed": sorted(allowed)},
        )


def _hash_source(text: str | None) -> str | None:
    if text is None:
        return None
    return _hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# TranslationService
# ---------------------------------------------------------------------------


def create_translation(
    db: _Session,
    *,
    roles: _Iterable[str],
    created_by: _uuid.UUID | None = None,
    payload: dict[str, _Any],
) -> _Translation:
    _require_permission(roles, "translation:create")

    entity_type = payload.get("entity_type") or payload.get("entityType")
    entity_id = payload.get("entity_id") or payload.get("entityId")
    locale = payload.get("locale")
    field_name = payload.get("field_name") or payload.get("fieldName")

    if not entity_type or not entity_id or not locale or not field_name:
        raise _ValidationError(
            "entity_type, entity_id, locale, and field_name are required"
        )
    _validate_entity_type(entity_type)
    _validate_field_name(field_name)
    _ensure_supported_locale(db, locale)
    eid = _as_uuid(entity_id)

    existing = _translations.get_scoped(
        db,
        entity_type=entity_type,
        entity_id=eid,
        locale=locale,
        field_name=field_name,
    )
    if existing is not None:
        raise _ConflictError(
            "Translation already exists for this scope",
            details={
                "entity_type": entity_type,
                "entity_id": str(eid),
                "locale": locale,
                "field_name": field_name,
            },
        )

    translated_value = payload.get("translated_value") or payload.get("translatedValue") or ""
    status = payload.get("status") or _T_DRAFT
    if status not in _T_STATUSES:
        raise _ValidationError(f"Invalid status: {status}")
    if status != _T_DRAFT and not translated_value.strip():
        raise _ValidationError(
            "Non-draft translations require translated_value"
        )

    source_hash = payload.get("source_hash") or payload.get("sourceHash")
    if source_hash is None and payload.get("source_text"):
        source_hash = _hash_source(payload["source_text"])

    data = {
        "entity_type": entity_type,
        "entity_id": eid,
        "locale": locale,
        "field_name": field_name,
        "translated_value": translated_value,
        "status": status,
        "source_hash": source_hash,
        "translated_by_user_id": created_by,
        "metadata_": payload.get("metadata") or payload.get("metadata_") or {},
    }
    row = _translations.create(db, data)
    _events.translation_created(db, row)
    return row


def update_translation(
    db: _Session,
    *,
    roles: _Iterable[str],
    translation_id: _uuid.UUID | str,
    payload: dict[str, _Any],
    updated_by: _uuid.UUID | None = None,
) -> _Translation:
    _require_permission(roles, "translation:update")
    row = _get_translation_or_404(db, translation_id)

    data: dict[str, _Any] = {}

    if "translated_value" in payload or "translatedValue" in payload:
        value = payload.get("translated_value")
        if value is None:
            value = payload.get("translatedValue")
        if value is None:
            raise _ValidationError("translated_value cannot be null")
        data["translated_value"] = value

    if "source_hash" in payload or "sourceHash" in payload:
        data["source_hash"] = payload.get("source_hash") or payload.get("sourceHash")

    if "metadata" in payload:
        data["metadata_"] = payload["metadata"] or {}

    new_status = payload.get("status")
    if new_status is not None:
        if new_status not in _T_STATUSES:
            raise _ValidationError(f"Invalid status: {new_status}")
        _assert_transition(row.status, new_status)
        # Publishing requires an active reviewer.
        if new_status == _T_PUBLISHED and row.status != _T_REVIEWED:
            raise _ConflictError(
                "Cannot publish before review",
                details={"current": row.status},
            )
        data["status"] = new_status
        if new_status == _T_DRAFT:
            # Rejection resets reviewer bookkeeping.
            data["reviewed_by_user_id"] = None

    if updated_by is not None:
        data["translated_by_user_id"] = updated_by

    if not data:
        return row
    updated = _translations.update(db, row, data)
    if data.get("status") == _T_DRAFT and row.status != _T_DRAFT:
        _events.translation_rejected(db, updated)
    elif data.get("status") == _T_PUBLISHED:
        _events.translation_published(db, updated)
    else:
        _events.translation_updated(db, updated)
    return updated


def review_translation(
    db: _Session,
    *,
    roles: _Iterable[str],
    translation_id: _uuid.UUID | str,
    reviewer_id: _uuid.UUID,
    approve: bool = True,
) -> _Translation:
    _require_permission(roles, "translation:review")
    row = _get_translation_or_404(db, translation_id)
    if approve:
        _assert_transition(row.status, _T_REVIEWED)
        updated = _translations.update(
            db,
            row,
            {"status": _T_REVIEWED, "reviewed_by_user_id": reviewer_id},
        )
        _events.translation_reviewed(db, updated)
        return updated
    # Rejection: send back to draft, clear reviewer.
    _assert_transition(row.status, _T_DRAFT)
    updated = _translations.update(
        db,
        row,
        {"status": _T_DRAFT, "reviewed_by_user_id": None},
    )
    _events.translation_rejected(db, updated)
    return updated


def publish_translation(
    db: _Session,
    *,
    roles: _Iterable[str],
    translation_id: _uuid.UUID | str,
) -> _Translation:
    _require_permission(roles, "translation:publish")
    row = _get_translation_or_404(db, translation_id)
    if row.status != _T_REVIEWED:
        raise _ConflictError(
            "Only reviewed translations can be published",
            details={"current": row.status},
        )
    if not row.translated_value or not row.translated_value.strip():
        raise _ConflictError("Cannot publish an empty translation")
    updated = _translations.update(db, row, {"status": _T_PUBLISHED})
    _events.translation_published(db, updated)
    return updated


def delete_translation(
    db: _Session,
    *,
    roles: _Iterable[str],
    translation_id: _uuid.UUID | str,
) -> None:
    _require_permission(roles, "translation:manage")
    row = _get_translation_or_404(db, translation_id)
    _events.translation_deleted(db, row)
    _translations.delete_translation(db, row)


def get_translation(
    db: _Session,
    *,
    roles: _Iterable[str],
    translation_id: _uuid.UUID | str,
) -> _Translation:
    _require_permission(roles, "translation:view")
    return _get_translation_or_404(db, translation_id)


def get_entity_translations(
    db: _Session,
    *,
    roles: _Iterable[str],
    entity_type: str,
    entity_id: _uuid.UUID | str,
    locale: str | None = None,
) -> list[_Translation]:
    _require_permission(roles, "translation:view")
    _validate_entity_type(entity_type)
    return _translations.list_by_entity(
        db,
        entity_type=entity_type,
        entity_id=_as_uuid(entity_id),
        locale=locale,
    )


def search_translations(
    db: _Session,
    *,
    roles: _Iterable[str],
    filters: dict[str, _Any],
) -> tuple[list[_Translation], int]:
    _require_permission(roles, "translation:view")
    normalized = dict(filters or {})
    et = normalized.get("entity_type")
    if et:
        _validate_entity_type(et)
    if normalized.get("status") and normalized["status"] not in _T_STATUSES:
        raise _ValidationError(f"Invalid status: {normalized['status']}")
    for key in ("entity_id", "translator_id", "reviewer_id"):
        val = normalized.get(key)
        if val is not None:
            normalized[key] = _as_uuid(val)
    return _translations.search(db, **normalized)


# ---------------------------------------------------------------------------
# TranslationJobService
# ---------------------------------------------------------------------------


def request_translation(
    db: _Session,
    *,
    roles: _Iterable[str],
    requested_by: _uuid.UUID | None,
    payload: dict[str, _Any],
) -> _TranslationJob:
    _require_permission(roles, "translation:create")
    entity_type = payload.get("entity_type") or payload.get("entityType")
    entity_id = payload.get("entity_id") or payload.get("entityId")
    source_locale = payload.get("source_locale") or payload.get("sourceLocale")
    target_locale = payload.get("target_locale") or payload.get("targetLocale")
    if not entity_type or not entity_id or not source_locale or not target_locale:
        raise _ValidationError(
            "entity_type, entity_id, source_locale, target_locale are required"
        )
    _validate_entity_type(entity_type)
    _validate_locale_code(source_locale)
    _ensure_supported_locale(db, target_locale)
    if source_locale == target_locale:
        raise _ValidationError("source_locale and target_locale must differ")

    data = {
        "entity_type": entity_type,
        "entity_id": _as_uuid(entity_id),
        "source_locale": source_locale,
        "target_locale": target_locale,
        "status": _JOB_PENDING,
        "provider": payload.get("provider"),
        "requested_by_user_id": requested_by,
        "requested_at": _dt.now(_tz.utc),
        "metadata_": payload.get("metadata") or {},
    }
    job = _translation_jobs.create_job(db, data)
    _events.job_requested(db, job)
    return job


def start_job(
    db: _Session,
    *,
    roles: _Iterable[str],
    job_id: _uuid.UUID | str,
) -> _TranslationJob:
    _require_permission(roles, "translation:manage")
    job = _get_job_or_404(db, job_id)
    _assert_job_transition(job.status, _JOB_PROCESSING)
    updated = _translation_jobs.update_job(db, job, {"status": _JOB_PROCESSING})
    _events.job_started(db, updated)
    return updated


def complete_job(
    db: _Session,
    *,
    roles: _Iterable[str],
    job_id: _uuid.UUID | str,
    metadata: dict[str, _Any] | None = None,
) -> _TranslationJob:
    _require_permission(roles, "translation:manage")
    job = _get_job_or_404(db, job_id)
    _assert_job_transition(job.status, _JOB_COMPLETED)
    updates: dict[str, _Any] = {
        "status": _JOB_COMPLETED,
        "completed_at": _dt.now(_tz.utc),
    }
    if metadata is not None:
        merged = dict(job.metadata_ or {})
        merged.update(metadata)
        updates["metadata_"] = merged
    updated = _translation_jobs.update_job(db, job, updates)
    _events.job_completed(db, updated)
    return updated


def fail_job(
    db: _Session,
    *,
    roles: _Iterable[str],
    job_id: _uuid.UUID | str,
    error: str | None = None,
) -> _TranslationJob:
    _require_permission(roles, "translation:manage")
    job = _get_job_or_404(db, job_id)
    _assert_job_transition(job.status, _JOB_FAILED)
    merged = dict(job.metadata_ or {})
    if error:
        merged["error"] = error
    updated = _translation_jobs.update_job(
        db,
        job,
        {
            "status": _JOB_FAILED,
            "completed_at": _dt.now(_tz.utc),
            "metadata_": merged,
        },
    )
    _events.job_failed(db, updated)
    return updated


def cancel_job(
    db: _Session,
    *,
    roles: _Iterable[str],
    job_id: _uuid.UUID | str,
) -> _TranslationJob:
    _require_permission(roles, "translation:manage")
    job = _get_job_or_404(db, job_id)
    _assert_job_transition(job.status, _JOB_CANCELLED)
    updated = _translation_jobs.cancel_job(db, job)
    _events.job_cancelled(db, updated)
    return updated


def get_job(
    db: _Session,
    *,
    roles: _Iterable[str],
    job_id: _uuid.UUID | str,
) -> _TranslationJob:
    _require_permission(roles, "translation:view")
    return _get_job_or_404(db, job_id)


def list_jobs(
    db: _Session,
    *,
    roles: _Iterable[str],
    filters: dict[str, _Any] | None = None,
) -> tuple[list[_TranslationJob], int]:
    _require_permission(roles, "translation:view")
    normalized = dict(filters or {})
    et = normalized.get("entity_type")
    if et:
        _validate_entity_type(et)
    status = normalized.get("status")
    if status and status not in _JOB_STATUSES:
        raise _ValidationError(f"Invalid job status: {status}")
    for key in ("entity_id", "requested_by_user_id"):
        val = normalized.get(key)
        if val is not None:
            normalized[key] = _as_uuid(val)
    return _translation_jobs.list_jobs(db, **normalized)


# ---------------------------------------------------------------------------
# TranslationLocaleService
# ---------------------------------------------------------------------------


def list_locales(
    db: _Session,
    *,
    roles: _Iterable[str] | None = None,
    enabled_only: bool = False,
) -> list[_TranslationLocale]:
    if roles is not None:
        _require_permission(roles, "translation:view")
    return _translation_locales.list_locales(db, enabled_only=enabled_only)


def get_default_locale(db: _Session) -> _TranslationLocale | None:
    return _translation_locales.get_default_locale(db)


def register_locale(
    db: _Session,
    *,
    roles: _Iterable[str],
    payload: dict[str, _Any],
) -> _TranslationLocale:
    _require_permission(roles, "translation:manage")
    locale = payload.get("locale")
    if not locale:
        raise _ValidationError("locale is required")
    _validate_locale_code(locale)
    if _translation_locales.get_locale(db, locale) is not None:
        raise _ConflictError(
            f"Locale '{locale}' is already registered", details={"locale": locale}
        )
    data = {
        "locale": locale,
        "display_name": payload.get("display_name")
        or payload.get("displayName")
        or locale,
        "native_name": payload.get("native_name") or payload.get("nativeName"),
        "rtl": bool(payload.get("rtl", False)),
        "enabled": bool(payload.get("enabled", True)),
        "default_locale": False,
        "sort_order": int(payload.get("sort_order") or payload.get("sortOrder") or 0),
    }
    row = _translation_locales.create(db, data)
    _events.locale_registered(db, row)
    if payload.get("default_locale") or payload.get("defaultLocale"):
        return set_default_locale(db, roles=roles, locale=row.locale)
    return row


def enable_locale(
    db: _Session, *, roles: _Iterable[str], locale: str
) -> _TranslationLocale:
    _require_permission(roles, "translation:manage")
    row = _translation_locales.get_locale(db, locale)
    if row is None:
        raise _NotFoundError("Locale not registered", details={"locale": locale})
    if row.enabled:
        return row
    updated = _translation_locales.update(db, row, {"enabled": True})
    _events.locale_enabled(db, updated)
    return updated


def disable_locale(
    db: _Session, *, roles: _Iterable[str], locale: str
) -> _TranslationLocale:
    _require_permission(roles, "translation:manage")
    row = _translation_locales.get_locale(db, locale)
    if row is None:
        raise _NotFoundError("Locale not registered", details={"locale": locale})
    if row.default_locale:
        raise _ConflictError(
            "Cannot disable the default locale; set another default first",
            details={"locale": locale},
        )
    if not row.enabled:
        return row
    updated = _translation_locales.update(db, row, {"enabled": False})
    _events.locale_disabled(db, updated)
    return updated


def update_locale(
    db: _Session,
    *,
    roles: _Iterable[str],
    locale: str,
    payload: dict[str, _Any],
) -> _TranslationLocale:
    """Patch metadata fields on a registered locale.

    ``enabled`` / ``default_locale`` toggles must go through the dedicated
    ``enable_locale`` / ``disable_locale`` / ``set_default_locale`` helpers.
    """
    _require_permission(roles, "translation:manage")
    row = _translation_locales.get_locale(db, locale)
    if row is None:
        raise _NotFoundError("Locale not registered", details={"locale": locale})
    data: dict[str, _Any] = {}
    for src, dst in (
        ("display_name", "display_name"),
        ("displayName", "display_name"),
        ("native_name", "native_name"),
        ("nativeName", "native_name"),
        ("rtl", "rtl"),
        ("sort_order", "sort_order"),
        ("sortOrder", "sort_order"),
    ):
        if src in payload and payload[src] is not None:
            data[dst] = payload[src]
    if not data:
        return row
    return _translation_locales.update(db, row, data)





def set_default_locale(
    db: _Session, *, roles: _Iterable[str], locale: str
) -> _TranslationLocale:
    _require_permission(roles, "translation:manage")
    row = _translation_locales.get_locale(db, locale)
    if row is None:
        raise _NotFoundError("Locale not registered", details={"locale": locale})
    if not row.enabled:
        raise _ConflictError(
            "Cannot mark a disabled locale as default",
            details={"locale": locale},
        )
    _translation_locales.clear_default(db)
    updated = _translation_locales.update(db, row, {"default_locale": True})
    _events.locale_default_changed(db, updated)
    return updated


__all__ = list(globals().get("__all__", [])) + [
    "create_translation",
    "update_translation",
    "review_translation",
    "publish_translation",
    "delete_translation",
    "get_translation",
    "get_entity_translations",
    "search_translations",
    "request_translation",
    "start_job",
    "complete_job",
    "fail_job",
    "cancel_job",
    "get_job",
    "list_jobs",
    "list_locales",
    "get_default_locale",
    "register_locale",
    "enable_locale",
    "disable_locale",
    "set_default_locale",
    "update_locale",
]

