"""Manual heartbeat helper (Phase 9.2).

No threads are started here; callers (Celery beat, a periodic task, or
tests) invoke :meth:`Heartbeat.beat` on their own cadence. The heartbeat
renews an underlying :class:`DistributedLock` and notifies subscribers
when the lease is lost.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from app.core.logging import get_logger

from .locking import DistributedLock

log = get_logger(__name__)


@dataclass
class HeartbeatState:
    beats: int = 0
    successes: int = 0
    failures: int = 0
    last_beat_at: float | None = None
    last_success_at: float | None = None
    last_failure_at: float | None = None
    last_error: str | None = None


class Heartbeat:
    """Periodic lock-renewal helper."""

    def __init__(
        self,
        lock: DistributedLock,
        *,
        interval_s: float = 10.0,
        on_lost: Callable[[DistributedLock], None] | None = None,
    ) -> None:
        if interval_s <= 0:
            raise ValueError("interval_s must be positive")
        self.lock = lock
        self.interval_s = interval_s
        self.on_lost = on_lost
        self.state = HeartbeatState()

    def beat(self) -> bool:
        self.state.beats += 1
        self.state.last_beat_at = time.monotonic()
        renewed = self.lock.renew()
        if renewed:
            self.state.successes += 1
            self.state.last_success_at = self.state.last_beat_at
            self.state.last_error = None
            return True
        self.state.failures += 1
        self.state.last_failure_at = self.state.last_beat_at
        self.state.last_error = "renew_failed"
        log.warning("ha.heartbeat.lost", key=self.lock.key, owner=self.lock.owner)
        if self.on_lost is not None:
            try:
                self.on_lost(self.lock)
            except Exception:  # noqa: BLE001 - callback must not break beat
                log.exception("ha.heartbeat.on_lost_failed")
        return False


__all__ = ["Heartbeat", "HeartbeatState"]
