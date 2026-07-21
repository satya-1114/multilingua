"""In-memory cache backend with LRU eviction and TTL support (Phase 9.4)."""
from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import Any

from .backend import CacheBackend, CacheEntry


class InMemoryCache(CacheBackend):
    """Thread-safe, size-bounded in-memory cache.

    * TTL is optional per-entry; expired entries are lazily removed on
      access and eagerly removed by :meth:`purge_expired`.
    * When ``max_size`` is exceeded, the least-recently-used entry is
      evicted.
    """

    def __init__(self, *, max_size: int = 1024, default_ttl: float | None = None):
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._sets = 0

    # -- reads ---------------------------------------------------------- #

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._entries[key]
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return entry.value

    def contains(self, key: str) -> bool:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.is_expired():
                return False
            return True

    # -- writes --------------------------------------------------------- #

    def set(self, key: str, value: Any, *, ttl: float | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = (
            time.monotonic() + effective_ttl if effective_ttl is not None else None
        )
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
            self._entries[key] = CacheEntry(value=value, expires_at=expires_at)
            self._sets += 1
            while len(self._entries) > self._max_size:
                self._entries.popitem(last=False)
                self._evictions += 1

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._entries.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    # -- maintenance ---------------------------------------------------- #

    def purge_expired(self) -> int:
        removed = 0
        now = time.monotonic()
        with self._lock:
            for key in list(self._entries.keys()):
                if self._entries[key].is_expired(now=now):
                    del self._entries[key]
                    removed += 1
        return removed

    # -- introspection -------------------------------------------------- #

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_ratio = round(self._hits / total, 6) if total else 0.0
            miss_ratio = round(self._misses / total, 6) if total else 0.0
            return {
                "backend": "memory",
                "size": len(self._entries),
                "maxSize": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "sets": self._sets,
                "evictions": self._evictions,
                "hitRatio": hit_ratio,
                "missRatio": miss_ratio,
            }

    def reset_stats(self) -> None:
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._sets = 0


__all__ = ["InMemoryCache"]