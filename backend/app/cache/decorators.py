"""Function-level caching decorator (Phase 9.4)."""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from .backend import CacheBackend, get_default_cache
from .keys import make_key


def cached(
    namespace: str,
    *,
    ttl: float | None = None,
    key_builder: Callable[..., str] | None = None,
    backend: CacheBackend | None = None,
):
    """Cache a pure(-ish) function's result by argument fingerprint."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        def _store() -> CacheBackend:
            return backend if backend is not None else get_default_cache()

        @wraps(fn)
        def wrapper(*args, **kwargs):
            store = _store()
            key = (
                key_builder(*args, **kwargs)
                if key_builder is not None
                else make_key(namespace, *args, **kwargs)
            )
            cached_value = store.get(key)
            if cached_value is not None:
                return cached_value
            value = fn(*args, **kwargs)
            if value is not None:
                store.set(key, value, ttl=ttl)
            return value

        wrapper.cache_key = lambda *a, **kw: (  # type: ignore[attr-defined]
            key_builder(*a, **kw)
            if key_builder is not None
            else make_key(namespace, *a, **kw)
        )
        wrapper.invalidate = lambda *a, **kw: (  # type: ignore[attr-defined]
            _store().delete(
                key_builder(*a, **kw)
                if key_builder is not None
                else make_key(namespace, *a, **kw)
            )
        )
        return wrapper

    return decorator


__all__ = ["cached"]