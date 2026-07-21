from __future__ import annotations

import time

import pytest

from app.runtime.ha.idempotency import (
    InMemoryIdempotencyStore,
    default_idempotency_store,
    set_default_idempotency_store,
)


@pytest.fixture
def store():
    return InMemoryIdempotencyStore()


def test_first_remember_is_new(store):
    is_new, rec = store.remember("k", ttl_s=60)
    assert is_new is True
    assert rec.key == "k"


def test_second_remember_is_duplicate(store):
    store.remember("k", ttl_s=60)
    is_new, _ = store.remember("k", ttl_s=60)
    assert is_new is False


def test_get_returns_record(store):
    store.remember("k", ttl_s=60)
    assert store.get("k") is not None


def test_get_returns_none_for_missing(store):
    assert store.get("nope") is None


def test_expired_record_is_forgotten(store):
    store.remember("k", ttl_s=0.05)
    time.sleep(0.1)
    assert store.get("k") is None


def test_expired_allows_new_remember(store):
    store.remember("k", ttl_s=0.05)
    time.sleep(0.1)
    is_new, _ = store.remember("k", ttl_s=60)
    assert is_new is True


def test_forget_removes_entry(store):
    store.remember("k", ttl_s=60)
    assert store.forget("k") is True
    assert store.get("k") is None


def test_forget_missing_returns_false(store):
    assert store.forget("k") is False


def test_reset_clears_all(store):
    store.remember("a", ttl_s=60)
    store.remember("b", ttl_s=60)
    store.reset()
    assert store.size() == 0


def test_empty_key_rejected(store):
    with pytest.raises(ValueError):
        store.remember("", ttl_s=60)


def test_bad_ttl_rejected(store):
    with pytest.raises(ValueError):
        store.remember("k", ttl_s=0)


def test_value_persisted(store):
    _, rec = store.remember("k", ttl_s=60, value={"x": 1})
    assert rec.value == {"x": 1}


def test_max_entries_evicts_oldest():
    s = InMemoryIdempotencyStore(max_entries=2)
    s.remember("a", ttl_s=60)
    time.sleep(0.01)
    s.remember("b", ttl_s=60)
    time.sleep(0.01)
    s.remember("c", ttl_s=60)
    assert s.get("a") is None
    assert s.get("b") is not None
    assert s.get("c") is not None


def test_max_entries_positive():
    with pytest.raises(ValueError):
        InMemoryIdempotencyStore(max_entries=0)


def test_default_store_singleton():
    a = default_idempotency_store()
    b = default_idempotency_store()
    assert a is b


def test_set_default_store_swap():
    orig = default_idempotency_store()
    new = InMemoryIdempotencyStore()
    prev = set_default_idempotency_store(new)
    try:
        assert default_idempotency_store() is new
        assert prev is orig
    finally:
        set_default_idempotency_store(orig)
