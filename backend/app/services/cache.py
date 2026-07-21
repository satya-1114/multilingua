"""Small caching layer with Redis when configured, in-process fallback.

Used by analytics, search, and report engines to memoise expensive
aggregations. Keys are namespaced by module + digest of the input.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

try:
    import redis  # type: ignore
    _redis_client: Any | None = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True) if settings.REDIS_URL else None
except Exception:  # pragma: no cover
    _redis_client = None

_local: dict[str, tuple[float, Any]] = {}


def _key(namespace: str, params: dict[str, Any]) -> str:
    raw = json.dumps(params, sort_keys=True, default=str)
    return f"cache:{namespace}:{hashlib.sha1(raw.encode()).hexdigest()[:24]}"


def get(namespace: str, params: dict[str, Any]) -> Any | None:
    k = _key(namespace, params)
    if _redis_client is not None:
        try:
            raw = _redis_client.get(k)
            return json.loads(raw) if raw else None
        except Exception as exc:  # pragma: no cover
            log.warning("cache_redis_get_failed", error=str(exc))
    entry = _local.get(k)
    if entry and entry[0] > time.time():
        return entry[1]
    if entry:
        _local.pop(k, None)
    return None


def set(namespace: str, params: dict[str, Any], value: Any, ttl_seconds: int = 60) -> None:
    k = _key(namespace, params)
    if _redis_client is not None:
        try:
            _redis_client.setex(k, ttl_seconds, json.dumps(value, default=str))
            return
        except Exception as exc:  # pragma: no cover
            log.warning("cache_redis_set_failed", error=str(exc))
    _local[k] = (time.time() + ttl_seconds, value)


def invalidate(namespace: str) -> None:
    prefix = f"cache:{namespace}:"
    if _redis_client is not None:
        try:
            for k in _redis_client.scan_iter(match=f"{prefix}*"):
                _redis_client.delete(k)
        except Exception:  # pragma: no cover
            pass
    for k in list(_local.keys()):
        if k.startswith(prefix):
            _local.pop(k, None)
