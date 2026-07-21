"""Distributed lock abstraction (Phase 9.2).

An interface-first design so a Redis/Postgres implementation can slot in
later without touching call sites. The default provider is fully
in-memory and thread-safe; it emulates lease-based semantics with a TTL
and monotonic clock.

Locks are lease-based: :meth:`acquire` succeeds only when either no lease
exists or the previous lease has expired. Callers must :meth:`release`
promptly or :meth:`renew` before the TTL elapses.
"""
from __future__ import annotations

import abc
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from app.core.logging import get_logger

log = get_logger(__name__)


class LockError(RuntimeError):
    """Base class for lock failures."""


class LockNotHeld(LockError):
    """Raised when release/renew is called on a lock the caller no longer owns."""


class LockAcquisitionFailed(LockError):
    """Raised by helpers that expect a lock to be acquired."""


@dataclass
class LockLease:
    """Lease record persisted by a :class:`LockProvider`."""

    key: str
    owner: str
    expires_at: float
    metadata: dict[str, str] = field(default_factory=dict)

    def is_expired(self, *, now: float | None = None) -> bool:
        return (now or time.monotonic()) >= self.expires_at


class LockProvider(abc.ABC):
    """Abstract lock backend."""

    name: str = "abstract"

    @abc.abstractmethod
    def try_acquire(
        self,
        key: str,
        *,
        owner: str,
        ttl_s: float,
        metadata: dict[str, str] | None = None,
    ) -> LockLease | None:
        ...

    @abc.abstractmethod
    def renew(self, key: str, *, owner: str, ttl_s: float) -> LockLease | None:
        ...

    @abc.abstractmethod
    def release(self, key: str, *, owner: str) -> bool:
        ...

    @abc.abstractmethod
    def inspect(self, key: str) -> LockLease | None:
        ...

    # helpers ------------------------------------------------------------- #

    def is_healthy(self) -> bool:
        return True


class InMemoryLockProvider(LockProvider):
    """Process-local, thread-safe lock provider (dev/CI default)."""

    name = "in_memory"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._leases: dict[str, LockLease] = {}

    def try_acquire(
        self,
        key: str,
        *,
        owner: str,
        ttl_s: float,
        metadata: dict[str, str] | None = None,
    ) -> LockLease | None:
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        now = time.monotonic()
        with self._lock:
            existing = self._leases.get(key)
            if existing is not None and not existing.is_expired(now=now):
                if existing.owner != owner:
                    return None
            lease = LockLease(
                key=key,
                owner=owner,
                expires_at=now + ttl_s,
                metadata=dict(metadata or {}),
            )
            self._leases[key] = lease
            log.info(
                "ha.lock.acquired",
                key=key, owner=owner, ttl_s=ttl_s, provider=self.name,
            )
            return lease

    def renew(self, key: str, *, owner: str, ttl_s: float) -> LockLease | None:
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        now = time.monotonic()
        with self._lock:
            existing = self._leases.get(key)
            if existing is None or existing.owner != owner:
                log.info("ha.lock.renew_denied", key=key, owner=owner)
                return None
            if existing.is_expired(now=now):
                log.info("ha.lock.renew_expired", key=key, owner=owner)
                return None
            existing.expires_at = now + ttl_s
            log.info("ha.lock.renewed", key=key, owner=owner, ttl_s=ttl_s)
            return existing

    def release(self, key: str, *, owner: str) -> bool:
        with self._lock:
            existing = self._leases.get(key)
            if existing is None:
                return False
            if existing.owner != owner:
                return False
            del self._leases[key]
            log.info("ha.lock.released", key=key, owner=owner)
            return True

    def inspect(self, key: str) -> LockLease | None:
        with self._lock:
            lease = self._leases.get(key)
            if lease is None:
                return None
            if lease.is_expired():
                log.info("ha.lock.expired", key=key, owner=lease.owner)
                return None
            return lease

    def reset(self) -> None:
        with self._lock:
            self._leases.clear()


class DistributedLock:
    """User-facing lock handle. Backed by any :class:`LockProvider`."""

    def __init__(
        self,
        provider: LockProvider,
        key: str,
        *,
        ttl_s: float = 30.0,
        owner: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.provider = provider
        self.key = key
        self.ttl_s = float(ttl_s)
        self.owner = owner or uuid.uuid4().hex
        self.metadata = dict(metadata or {})
        self._lease: LockLease | None = None

    # -- state ---------------------------------------------------------- #

    @property
    def is_held(self) -> bool:
        lease = self._lease
        return lease is not None and not lease.is_expired()

    @property
    def lease(self) -> LockLease | None:
        return self._lease

    # -- operations ----------------------------------------------------- #

    def acquire(self, *, ttl_s: float | None = None) -> bool:
        lease = self.provider.try_acquire(
            self.key,
            owner=self.owner,
            ttl_s=ttl_s or self.ttl_s,
            metadata=self.metadata,
        )
        self._lease = lease
        return lease is not None

    def acquire_or_raise(self) -> LockLease:
        if not self.acquire():
            raise LockAcquisitionFailed(f"could not acquire lock {self.key!r}")
        assert self._lease is not None
        return self._lease

    def renew(self, *, ttl_s: float | None = None) -> bool:
        if self._lease is None:
            return False
        lease = self.provider.renew(
            self.key, owner=self.owner, ttl_s=ttl_s or self.ttl_s
        )
        if lease is None:
            self._lease = None
            return False
        self._lease = lease
        return True

    def release(self) -> bool:
        if self._lease is None:
            return False
        released = self.provider.release(self.key, owner=self.owner)
        self._lease = None
        return released

    # -- context manager ------------------------------------------------ #

    def __enter__(self) -> "DistributedLock":
        if not self.acquire():
            raise LockAcquisitionFailed(f"could not acquire lock {self.key!r}")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


# -- module-level defaults --------------------------------------------- #

_default_provider: LockProvider = InMemoryLockProvider()


def default_lock_provider() -> LockProvider:
    return _default_provider


def set_default_lock_provider(provider: LockProvider) -> LockProvider:
    global _default_provider
    prev = _default_provider
    _default_provider = provider
    return prev


@contextmanager
def acquire(key: str, *, ttl_s: float = 30.0, owner: str | None = None) -> Iterator[DistributedLock]:
    lock = DistributedLock(default_lock_provider(), key, ttl_s=ttl_s, owner=owner)
    with lock as held:
        yield held


__all__ = [
    "DistributedLock",
    "InMemoryLockProvider",
    "LockAcquisitionFailed",
    "LockError",
    "LockLease",
    "LockNotHeld",
    "LockProvider",
    "acquire",
    "default_lock_provider",
    "set_default_lock_provider",
]
