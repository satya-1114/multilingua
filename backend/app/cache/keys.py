"""Deterministic cache key construction (Phase 9.4)."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical(value: Any) -> Any:
    """Return a JSON-safe representation with sorted mapping keys."""
    if isinstance(value, dict):
        return {k: _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def make_key(namespace: str, *parts: Any, **fields: Any) -> str:
    """Build a stable cache key from a namespace and arbitrary parts.

    Long or complex keys are hashed to keep the final key compact and
    safe for any backend.
    """
    if not namespace:
        raise ValueError("namespace is required")
    payload = {
        "parts": [_canonical(p) for p in parts],
        "fields": _canonical(fields),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    if len(encoded) <= 96 and not any(c.isspace() for c in encoded):
        # Short & clean — keep it readable.
        return f"{namespace}:{encoded}"
    digest = hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:24]
    return f"{namespace}:{digest}"


__all__ = ["make_key"]