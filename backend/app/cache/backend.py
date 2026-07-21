"""Abstract cache backend interface (Phase 9.4)."""
from __future__ import annotations

import abc
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: float | None  # monotonic seconds; None = no TTL

    def is_expired(self, *, now: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        moment = now if now is not None else time.monotonic()
        return moment >= self.expires_at


class CacheBackend(abc.ABC):
    """Interface every cache implementation must satisfy."""

    @abc.abstractmethod
    def get(self, key: str) -> Any | None: ...

    @abc.abstractmethod
    def set(self, key: str, value: Any, *, ttl: float | None = None) -> None: ...

    @abc.abstractmethod
    def delete(self, key: str) -> bool: ...

    @abc.abstractmethod
    def clear(self) -> None: ...

    @abc.abstractmethod
    def stats(self) -> dict[str, Any]: ...

    # Convenience helpers – shared implementation is fine.
    def get_or_set(
        self, key: str, factory, *, ttl: float | None = None
    ) -> Any:
        value = self.get(key)
        if value is not None:
            return value
        value = factory()
        self.set(key, value, ttl=ttl)
        return value


_default_backend_lock = RLock()
_default_backend: CacheBackend | None = None


def get_default_cache() -> CacheBackend:
    global _default_backend
    with _default_backend_lock:
        if _default_backend is None:
            from .memory import InMemoryCache

            _default_backend = InMemoryCache()
        return _default_backend


def set_default_cache(cache: CacheBackend) -> CacheBackend:
    global _default_backend
    with _default_backend_lock:
        _default_backend = cache
    return cache


__all__ = [
    "CacheBackend",
    "CacheEntry",
    "get_default_cache",
    "set_default_cache",
]