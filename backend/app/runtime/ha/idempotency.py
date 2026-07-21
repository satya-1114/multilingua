"""Idempotency cache abstraction (Phase 9.2).

Used by the webhook handler and the runtime executor to suppress
duplicate side-effects. The default implementation is a bounded,
thread-safe in-memory TTL cache.
"""
from __future__ import annotations

import abc
import threading
import time
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class IdempotencyRecord:
    key: str
    stored_at: float
    expires_at: float
    value: Any = None

    def is_expired(self, *, now: float | None = None) -> bool:
        return (now or time.monotonic()) >= self.expires_at


class IdempotencyStore(abc.ABC):
    """Abstract idempotency store."""

    name: str = "abstract"

    @abc.abstractmethod
    def remember(
        self, key: str, *, ttl_s: float, value: Any = None
    ) -> tuple[bool, IdempotencyRecord]:
        """Store *key*. Return ``(is_new, record)``."""

    @abc.abstractmethod
    def get(self, key: str) -> IdempotencyRecord | None:
        ...

    @abc.abstractmethod
    def forget(self, key: str) -> bool:
        ...

    def reset(self) -> None:  # pragma: no cover - default noop
        pass


class InMemoryIdempotencyStore(IdempotencyStore):
    name = "in_memory"

    def __init__(self, *, max_entries: int = 10_000) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._max = max_entries
        self._lock = threading.RLock()
        self._records: dict[str, IdempotencyRecord] = {}

    def _prune_locked(self, now: float) -> None:
        for k, r in list(self._records.items()):
            if r.is_expired(now=now):
                del self._records[k]
        if len(self._records) >= self._max:
            # evict oldest first
            ordered = sorted(self._records.items(), key=lambda kv: kv[1].stored_at)
            for k, _ in ordered[: len(self._records) - self._max + 1]:
                del self._records[k]

    def remember(
        self, key: str, *, ttl_s: float, value: Any = None
    ) -> tuple[bool, IdempotencyRecord]:
        if not key:
            raise ValueError("key must be non-empty")
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        now = time.monotonic()
        with self._lock:
            self._prune_locked(now)
            existing = self._records.get(key)
            if existing is not None and not existing.is_expired(now=now):
                log.info("ha.idempotency.duplicate", key=key)
                return False, existing
            record = IdempotencyRecord(
                key=key,
                stored_at=now,
                expires_at=now + ttl_s,
                value=value,
            )
            self._records[key] = record
            log.info("ha.idempotency.stored", key=key, ttl_s=ttl_s)
            return True, record

    def get(self, key: str) -> IdempotencyRecord | None:
        with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            if record.is_expired():
                del self._records[key]
                return None
            return record

    def forget(self, key: str) -> bool:
        with self._lock:
            return self._records.pop(key, None) is not None

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._records)


_default: IdempotencyStore = InMemoryIdempotencyStore()


def default_idempotency_store() -> IdempotencyStore:
    return _default


def set_default_idempotency_store(store: IdempotencyStore) -> IdempotencyStore:
    global _default
    prev = _default
    _default = store
    return prev


__all__ = [
    "IdempotencyRecord",
    "IdempotencyStore",
    "InMemoryIdempotencyStore",
    "default_idempotency_store",
    "set_default_idempotency_store",
]
