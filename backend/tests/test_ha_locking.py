from __future__ import annotations

import threading
import time

import pytest

from app.runtime.ha.locking import (
    DistributedLock,
    InMemoryLockProvider,
    LockAcquisitionFailed,
    acquire,
    default_lock_provider,
    set_default_lock_provider,
)


@pytest.fixture
def provider():
    return InMemoryLockProvider()


def test_acquire_returns_lease(provider):
    lease = provider.try_acquire("k", owner="a", ttl_s=1)
    assert lease is not None
    assert lease.owner == "a"


def test_second_owner_blocked(provider):
    provider.try_acquire("k", owner="a", ttl_s=5)
    assert provider.try_acquire("k", owner="b", ttl_s=5) is None


def test_same_owner_reacquire_ok(provider):
    provider.try_acquire("k", owner="a", ttl_s=5)
    assert provider.try_acquire("k", owner="a", ttl_s=5) is not None


def test_release_frees_lock(provider):
    provider.try_acquire("k", owner="a", ttl_s=5)
    assert provider.release("k", owner="a")
    assert provider.try_acquire("k", owner="b", ttl_s=5) is not None


def test_release_wrong_owner_denied(provider):
    provider.try_acquire("k", owner="a", ttl_s=5)
    assert provider.release("k", owner="b") is False


def test_release_missing_returns_false(provider):
    assert provider.release("nope", owner="a") is False


def test_expiration_allows_new_owner(provider):
    provider.try_acquire("k", owner="a", ttl_s=0.05)
    time.sleep(0.1)
    assert provider.try_acquire("k", owner="b", ttl_s=1) is not None


def test_renew_extends_lease(provider):
    provider.try_acquire("k", owner="a", ttl_s=0.1)
    lease = provider.renew("k", owner="a", ttl_s=5)
    assert lease is not None
    assert lease.expires_at - time.monotonic() > 1


def test_renew_wrong_owner_denied(provider):
    provider.try_acquire("k", owner="a", ttl_s=5)
    assert provider.renew("k", owner="b", ttl_s=5) is None


def test_renew_expired_denied(provider):
    provider.try_acquire("k", owner="a", ttl_s=0.05)
    time.sleep(0.1)
    assert provider.renew("k", owner="a", ttl_s=5) is None


def test_ttl_must_be_positive(provider):
    with pytest.raises(ValueError):
        provider.try_acquire("k", owner="a", ttl_s=0)


def test_inspect_returns_active_lease(provider):
    provider.try_acquire("k", owner="a", ttl_s=5)
    assert provider.inspect("k") is not None


def test_inspect_returns_none_when_missing(provider):
    assert provider.inspect("k") is None


def test_inspect_returns_none_when_expired(provider):
    provider.try_acquire("k", owner="a", ttl_s=0.05)
    time.sleep(0.1)
    assert provider.inspect("k") is None


def test_reset_clears_leases(provider):
    provider.try_acquire("k", owner="a", ttl_s=5)
    provider.reset()
    assert provider.inspect("k") is None


def test_distributed_lock_acquire(provider):
    lock = DistributedLock(provider, "k", ttl_s=1)
    assert lock.acquire()
    assert lock.is_held


def test_distributed_lock_second_holder_blocked(provider):
    a = DistributedLock(provider, "k", ttl_s=5, owner="a")
    b = DistributedLock(provider, "k", ttl_s=5, owner="b")
    a.acquire()
    assert b.acquire() is False


def test_distributed_lock_release(provider):
    lock = DistributedLock(provider, "k", ttl_s=1)
    lock.acquire()
    assert lock.release()
    assert not lock.is_held


def test_distributed_lock_renew(provider):
    lock = DistributedLock(provider, "k", ttl_s=0.5)
    lock.acquire()
    assert lock.renew(ttl_s=5)


def test_distributed_lock_renew_after_loss_returns_false(provider):
    lock = DistributedLock(provider, "k", ttl_s=0.05)
    lock.acquire()
    time.sleep(0.1)
    # someone else takes it
    provider.try_acquire("k", owner="other", ttl_s=5)
    assert lock.renew() is False
    assert not lock.is_held


def test_distributed_lock_context_manager(provider):
    lock = DistributedLock(provider, "k", ttl_s=1)
    with lock:
        assert lock.is_held
    assert not lock.is_held


def test_distributed_lock_context_manager_raises_on_conflict(provider):
    provider.try_acquire("k", owner="held", ttl_s=5)
    lock = DistributedLock(provider, "k", ttl_s=1)
    with pytest.raises(LockAcquisitionFailed):
        with lock:
            pass


def test_acquire_or_raise_success(provider):
    lock = DistributedLock(provider, "k", ttl_s=1)
    lease = lock.acquire_or_raise()
    assert lease.owner == lock.owner


def test_acquire_or_raise_failure(provider):
    provider.try_acquire("k", owner="held", ttl_s=5)
    lock = DistributedLock(provider, "k", ttl_s=1)
    with pytest.raises(LockAcquisitionFailed):
        lock.acquire_or_raise()


def test_release_without_acquire_is_noop(provider):
    lock = DistributedLock(provider, "k", ttl_s=1)
    assert lock.release() is False


def test_module_helper_acquire():
    with acquire("mod-k", ttl_s=1) as held:
        assert held.is_held


def test_set_default_lock_provider_swap():
    orig = default_lock_provider()
    new = InMemoryLockProvider()
    prev = set_default_lock_provider(new)
    try:
        assert default_lock_provider() is new
        assert prev is orig
    finally:
        set_default_lock_provider(orig)


def test_concurrent_acquire_only_one_wins(provider):
    results = []

    def worker(name):
        results.append(bool(provider.try_acquire("k", owner=name, ttl_s=5)))

    threads = [threading.Thread(target=worker, args=(f"o{i}",)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(1 for r in results if r) == 1


def test_is_healthy_default_true(provider):
    assert provider.is_healthy() is True
