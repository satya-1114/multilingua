from __future__ import annotations

import time

import pytest

from app.runtime.ha.heartbeat import Heartbeat
from app.runtime.ha.locking import DistributedLock, InMemoryLockProvider


@pytest.fixture
def held_lock():
    provider = InMemoryLockProvider()
    lock = DistributedLock(provider, "k", ttl_s=1)
    lock.acquire()
    return lock


def test_beat_success_records_state(held_lock):
    hb = Heartbeat(held_lock, interval_s=0.5)
    assert hb.beat()
    assert hb.state.beats == 1
    assert hb.state.successes == 1
    assert hb.state.failures == 0


def test_multiple_beats_accumulate(held_lock):
    hb = Heartbeat(held_lock, interval_s=0.5)
    for _ in range(3):
        hb.beat()
    assert hb.state.beats == 3
    assert hb.state.successes == 3


def test_beat_after_loss_records_failure():
    provider = InMemoryLockProvider()
    lock = DistributedLock(provider, "k", ttl_s=0.05)
    lock.acquire()
    time.sleep(0.1)
    provider.try_acquire("k", owner="other", ttl_s=5)
    hb = Heartbeat(lock, interval_s=0.5)
    assert hb.beat() is False
    assert hb.state.failures == 1
    assert hb.state.last_error == "renew_failed"


def test_on_lost_callback(held_lock):
    called = []
    provider = held_lock.provider
    provider.try_acquire("k", owner="other", ttl_s=5)  # override
    # emulate we lost lease
    held_lock._lease.expires_at = time.monotonic() - 1
    hb = Heartbeat(held_lock, interval_s=0.5, on_lost=lambda l: called.append(l.key))
    hb.beat()
    assert called == ["k"]


def test_on_lost_swallows_exceptions(held_lock):
    def bad(_):
        raise RuntimeError("boom")

    provider = held_lock.provider
    provider.try_acquire("k", owner="other", ttl_s=5)
    held_lock._lease.expires_at = time.monotonic() - 1
    hb = Heartbeat(held_lock, interval_s=0.5, on_lost=bad)
    hb.beat()  # must not raise


def test_interval_validated(held_lock):
    with pytest.raises(ValueError):
        Heartbeat(held_lock, interval_s=0)
