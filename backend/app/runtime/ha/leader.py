"""Leader election abstraction (Phase 9.2).

Leader election is built on top of :mod:`app.runtime.ha.locking`. The
elector attempts to acquire a well-known lock; the first successful
acquire wins. Followers periodically retry so they can take over when
the leader drops.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Callable

from app.core.logging import get_logger

from .locking import DistributedLock, LockLease, LockProvider, default_lock_provider
try:
    from app.observability.metrics import observability_metrics as _obs_metrics
except Exception:  # pragma: no cover
    _obs_metrics = None  # type: ignore

log = get_logger(__name__)


LEADER_LOCK_KEY = "workflow.scheduler.leader"


@dataclass
class LeaderStatus:
    key: str
    node_id: str
    is_leader: bool
    lease_expires_at: float | None
    acquired_at: float | None
    lost_at: float | None
    provider: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "nodeId": self.node_id,
            "isLeader": self.is_leader,
            "leaseExpiresAt": self.lease_expires_at,
            "acquiredAt": self.acquired_at,
            "lostAt": self.lost_at,
            "provider": self.provider,
        }


class LeaderElector:
    """Cooperative leader election driven by manual ticks."""

    def __init__(
        self,
        *,
        key: str = LEADER_LOCK_KEY,
        provider: LockProvider | None = None,
        ttl_s: float = 30.0,
        node_id: str | None = None,
        on_elected: Callable[["LeaderElector"], None] | None = None,
        on_lost: Callable[["LeaderElector"], None] | None = None,
    ) -> None:
        if ttl_s <= 0:
            raise ValueError("ttl_s must be positive")
        self.key = key
        self.provider = provider or default_lock_provider()
        self.ttl_s = ttl_s
        self.node_id = node_id or uuid.uuid4().hex
        self.on_elected = on_elected
        self.on_lost = on_lost
        self._lock = DistributedLock(
            self.provider, key, ttl_s=ttl_s, owner=self.node_id,
        )
        self._is_leader = False
        self._acquired_at: float | None = None
        self._lost_at: float | None = None

    # -- state ---------------------------------------------------------- #

    @property
    def is_leader(self) -> bool:
        if not self._is_leader:
            return False
        if not self._lock.is_held:
            self._transition_to_follower()
            return False
        return True

    def status(self) -> LeaderStatus:
        lease: LockLease | None = self._lock.lease if self._is_leader else None
        return LeaderStatus(
            key=self.key,
            node_id=self.node_id,
            is_leader=self.is_leader,
            lease_expires_at=lease.expires_at if lease else None,
            acquired_at=self._acquired_at,
            lost_at=self._lost_at,
            provider=type(self.provider).__name__,
        )

    # -- transitions ---------------------------------------------------- #

    def try_acquire(self) -> bool:
        if self._is_leader and self._lock.is_held:
            return True
        acquired = self._lock.acquire()
        if acquired:
            self._transition_to_leader()
            return True
        # ensure state stays follower
        if self._is_leader:
            self._transition_to_follower()
        return False

    def renew(self) -> bool:
        if not self._is_leader:
            return False
        renewed = self._lock.renew()
        if not renewed:
            self._transition_to_follower()
        return renewed

    def tick(self) -> bool:
        """Try to acquire (as follower) or renew (as leader)."""
        if self._is_leader:
            return self.renew()
        return self.try_acquire()

    def resign(self) -> None:
        if self._is_leader:
            self._lock.release()
            self._transition_to_follower()

    # -- internals ------------------------------------------------------ #

    def _transition_to_leader(self) -> None:
        was_leader = self._is_leader
        self._is_leader = True
        self._acquired_at = time.time()
        log.info(
            "ha.leader.elected", key=self.key, node_id=self.node_id, was_leader=was_leader,
        )
        if not was_leader and _obs_metrics is not None:
            try:
                _obs_metrics.record_leader_elected(self.node_id)
            except Exception:  # pragma: no cover
                pass
        if not was_leader and self.on_elected is not None:
            try:
                self.on_elected(self)
            except Exception:  # noqa: BLE001
                log.exception("ha.leader.on_elected_failed")

    def _transition_to_follower(self) -> None:
        was_leader = self._is_leader
        self._is_leader = False
        self._lost_at = time.time()
        if was_leader:
            log.warning("ha.leader.lost", key=self.key, node_id=self.node_id)
            if _obs_metrics is not None:
                try:
                    _obs_metrics.record_leader_lost(self.node_id)
                except Exception:  # pragma: no cover
                    pass
            if self.on_lost is not None:
                try:
                    self.on_lost(self)
                except Exception:  # noqa: BLE001
                    log.exception("ha.leader.on_lost_failed")


__all__ = ["LEADER_LOCK_KEY", "LeaderElector", "LeaderStatus"]
