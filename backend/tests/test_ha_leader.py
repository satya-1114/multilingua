from __future__ import annotations

import time

import pytest

from app.runtime.ha.election import (
    default_elector,
    reset_default_elector,
    set_default_elector,
)
from app.runtime.ha.leader import LEADER_LOCK_KEY, LeaderElector
from app.runtime.ha.locking import InMemoryLockProvider


@pytest.fixture
def provider():
    return InMemoryLockProvider()


@pytest.fixture(autouse=True)
def _reset_default_elector():
    reset_default_elector()
    yield
    reset_default_elector()


def test_first_acquire_makes_leader(provider):
    e = LeaderElector(provider=provider, ttl_s=1)
    assert e.try_acquire()
    assert e.is_leader


def test_second_elector_becomes_follower(provider):
    a = LeaderElector(provider=provider, ttl_s=5, node_id="a")
    b = LeaderElector(provider=provider, ttl_s=5, node_id="b")
    a.try_acquire()
    assert b.try_acquire() is False
    assert not b.is_leader


def test_leader_renews(provider):
    e = LeaderElector(provider=provider, ttl_s=0.5)
    e.try_acquire()
    assert e.renew()


def test_follower_renew_returns_false(provider):
    e = LeaderElector(provider=provider, ttl_s=1)
    assert e.renew() is False


def test_leader_loses_after_expiry(provider):
    a = LeaderElector(provider=provider, ttl_s=0.05, node_id="a")
    a.try_acquire()
    time.sleep(0.1)
    b = LeaderElector(provider=provider, ttl_s=5, node_id="b")
    assert b.try_acquire()
    # a discovers loss on tick
    assert a.renew() is False
    assert not a.is_leader


def test_resign_frees_leadership(provider):
    a = LeaderElector(provider=provider, ttl_s=5, node_id="a")
    b = LeaderElector(provider=provider, ttl_s=5, node_id="b")
    a.try_acquire()
    a.resign()
    assert not a.is_leader
    assert b.try_acquire()


def test_tick_leader_renews(provider):
    e = LeaderElector(provider=provider, ttl_s=1)
    e.try_acquire()
    assert e.tick() is True


def test_tick_follower_tries_acquire(provider):
    e = LeaderElector(provider=provider, ttl_s=1)
    assert e.tick() is True
    assert e.is_leader


def test_on_elected_callback_fires(provider):
    calls = []
    e = LeaderElector(provider=provider, ttl_s=1, on_elected=lambda x: calls.append("e"))
    e.try_acquire()
    assert calls == ["e"]


def test_on_elected_only_fires_on_transition(provider):
    calls = []
    e = LeaderElector(provider=provider, ttl_s=5, on_elected=lambda x: calls.append("e"))
    e.try_acquire()
    e.try_acquire()  # already leader
    assert calls == ["e"]


def test_on_lost_callback_fires(provider):
    calls = []
    a = LeaderElector(provider=provider, ttl_s=0.05, node_id="a",
                      on_lost=lambda x: calls.append("lost"))
    a.try_acquire()
    time.sleep(0.1)
    provider.try_acquire(LEADER_LOCK_KEY, owner="b", ttl_s=5)
    a.renew()  # discovers loss
    assert calls == ["lost"]


def test_on_elected_exception_swallowed(provider):
    def boom(_):
        raise RuntimeError("bad callback")

    e = LeaderElector(provider=provider, ttl_s=1, on_elected=boom)
    assert e.try_acquire()  # does not propagate


def test_status_when_follower(provider):
    e = LeaderElector(provider=provider, ttl_s=1)
    s = e.status().to_dict()
    assert s["isLeader"] is False
    assert s["provider"] == "InMemoryLockProvider"


def test_status_when_leader(provider):
    e = LeaderElector(provider=provider, ttl_s=1)
    e.try_acquire()
    s = e.status().to_dict()
    assert s["isLeader"] is True
    assert s["nodeId"] == e.node_id


def test_ttl_must_be_positive(provider):
    with pytest.raises(ValueError):
        LeaderElector(provider=provider, ttl_s=0)


def test_default_elector_singleton():
    a = default_elector()
    b = default_elector()
    assert a is b


def test_set_default_elector_swap():
    orig = default_elector()
    new = LeaderElector(provider=InMemoryLockProvider(), ttl_s=1)
    prev = set_default_elector(new)
    try:
        assert default_elector() is new
        assert prev is orig
    finally:
        set_default_elector(orig)


def test_reset_creates_new_default():
    a = default_elector()
    reset_default_elector()
    b = default_elector()
    assert a is not b


def test_two_electors_isolated_by_key(provider):
    a = LeaderElector(provider=provider, ttl_s=5, key="k1")
    b = LeaderElector(provider=provider, ttl_s=5, key="k2")
    assert a.try_acquire()
    assert b.try_acquire()


def test_leader_lost_when_lease_gone(provider):
    e = LeaderElector(provider=provider, ttl_s=0.05)
    e.try_acquire()
    time.sleep(0.1)
    # accessing is_leader detects loss
    assert e.is_leader is False
