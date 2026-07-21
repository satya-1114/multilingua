"""High-availability primitives for the workflow runtime (Phase 9.2)."""
from __future__ import annotations

from .election import default_elector, reset_default_elector, set_default_elector
from .heartbeat import Heartbeat, HeartbeatState
from .idempotency import (
    IdempotencyRecord,
    IdempotencyStore,
    InMemoryIdempotencyStore,
    default_idempotency_store,
    set_default_idempotency_store,
)
from .leader import LEADER_LOCK_KEY, LeaderElector, LeaderStatus
from .locking import (
    DistributedLock,
    InMemoryLockProvider,
    LockAcquisitionFailed,
    LockError,
    LockLease,
    LockNotHeld,
    LockProvider,
    acquire,
    default_lock_provider,
    set_default_lock_provider,
)

__all__ = [
    "DistributedLock",
    "Heartbeat",
    "HeartbeatState",
    "IdempotencyRecord",
    "IdempotencyStore",
    "InMemoryIdempotencyStore",
    "InMemoryLockProvider",
    "LEADER_LOCK_KEY",
    "LeaderElector",
    "LeaderStatus",
    "LockAcquisitionFailed",
    "LockError",
    "LockLease",
    "LockNotHeld",
    "LockProvider",
    "acquire",
    "default_elector",
    "default_idempotency_store",
    "default_lock_provider",
    "reset_default_elector",
    "set_default_elector",
    "set_default_idempotency_store",
    "set_default_lock_provider",
]
