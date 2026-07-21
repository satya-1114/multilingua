from __future__ import annotations

import time

import pytest

from app.cache import (
    CacheBackend,
    InMemoryCache,
    cached,
    get_default_cache,
    make_key,
    set_default_cache,
)
from app.cache.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    batched,
    normalize_page_params,
    page_envelope,
    paginate_sequence,
)


# --------------------------------------------------------------------------- #
# InMemoryCache
# --------------------------------------------------------------------------- #


def test_set_and_get_returns_value():
    cache = InMemoryCache()
    cache.set("a", 1)
    assert cache.get("a") == 1


def test_get_missing_key_returns_none():
    cache = InMemoryCache()
    assert cache.get("missing") is None


def test_contains_returns_true_when_present():
    cache = InMemoryCache()
    cache.set("a", 1)
    assert cache.contains("a") is True


def test_contains_returns_false_when_absent():
    cache = InMemoryCache()
    assert cache.contains("missing") is False


def test_delete_removes_entry():
    cache = InMemoryCache()
    cache.set("a", 1)
    assert cache.delete("a") is True
    assert cache.get("a") is None


def test_delete_returns_false_when_missing():
    cache = InMemoryCache()
    assert cache.delete("nope") is False


def test_clear_empties_cache():
    cache = InMemoryCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0


def test_len_reflects_size():
    cache = InMemoryCache()
    assert len(cache) == 0
    cache.set("a", 1)
    cache.set("b", 2)
    assert len(cache) == 2


def test_set_overwrite_updates_value():
    cache = InMemoryCache()
    cache.set("a", 1)
    cache.set("a", 2)
    assert cache.get("a") == 2


def test_ttl_expires_entry():
    cache = InMemoryCache()
    cache.set("a", 1, ttl=0.01)
    time.sleep(0.02)
    assert cache.get("a") is None


def test_ttl_none_never_expires():
    cache = InMemoryCache(default_ttl=None)
    cache.set("a", 1)
    assert cache.get("a") == 1


def test_default_ttl_applied_when_no_explicit_ttl():
    cache = InMemoryCache(default_ttl=0.01)
    cache.set("a", 1)
    time.sleep(0.02)
    assert cache.get("a") is None


def test_explicit_ttl_overrides_default_ttl():
    cache = InMemoryCache(default_ttl=0.001)
    cache.set("a", 1, ttl=5.0)
    time.sleep(0.01)
    assert cache.get("a") == 1


def test_max_size_evicts_least_recently_used():
    cache = InMemoryCache(max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # evicts "a"
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


def test_lru_promotes_on_get():
    cache = InMemoryCache(max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # promote a
    cache.set("c", 3)  # should evict b now
    assert cache.get("b") is None
    assert cache.get("a") == 1


def test_invalid_max_size_rejected():
    with pytest.raises(ValueError):
        InMemoryCache(max_size=0)


def test_stats_reports_hits_misses():
    cache = InMemoryCache()
    cache.set("a", 1)
    cache.get("a")
    cache.get("missing")
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hitRatio"] == 0.5
    assert stats["missRatio"] == 0.5


def test_stats_zero_activity_ratios_are_zero():
    stats = InMemoryCache().stats()
    assert stats["hitRatio"] == 0.0
    assert stats["missRatio"] == 0.0


def test_stats_reports_evictions():
    cache = InMemoryCache(max_size=1)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.stats()["evictions"] == 1


def test_stats_reports_sets():
    cache = InMemoryCache()
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.stats()["sets"] == 2


def test_reset_stats_zeros_counters():
    cache = InMemoryCache()
    cache.set("a", 1)
    cache.get("a")
    cache.reset_stats()
    stats = cache.stats()
    assert stats["hits"] == 0 and stats["sets"] == 0


def test_purge_expired_removes_only_expired():
    cache = InMemoryCache()
    cache.set("a", 1, ttl=0.01)
    cache.set("b", 2)
    time.sleep(0.02)
    removed = cache.purge_expired()
    assert removed == 1
    assert cache.get("b") == 2


def test_purge_expired_returns_zero_when_none():
    cache = InMemoryCache()
    cache.set("a", 1)
    assert cache.purge_expired() == 0


def test_get_or_set_populates_on_miss():
    cache = InMemoryCache()
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return "v"

    assert cache.get_or_set("k", factory) == "v"
    assert cache.get_or_set("k", factory) == "v"
    assert calls["n"] == 1


def test_get_or_set_respects_ttl():
    cache = InMemoryCache()
    cache.get_or_set("k", lambda: "v", ttl=0.01)
    time.sleep(0.02)
    assert cache.get("k") is None


def test_cache_backend_is_abstract():
    with pytest.raises(TypeError):
        CacheBackend()  # type: ignore[abstract]


def test_stats_backend_name_is_memory():
    assert InMemoryCache().stats()["backend"] == "memory"


def test_expired_entry_treated_as_miss_in_contains():
    cache = InMemoryCache()
    cache.set("a", 1, ttl=0.01)
    time.sleep(0.02)
    assert cache.contains("a") is False


# --------------------------------------------------------------------------- #
# Default cache
# --------------------------------------------------------------------------- #


def test_get_default_cache_returns_singleton():
    a = get_default_cache()
    b = get_default_cache()
    assert a is b


def test_set_default_cache_replaces_singleton():
    original = get_default_cache()
    replacement = InMemoryCache()
    set_default_cache(replacement)
    try:
        assert get_default_cache() is replacement
    finally:
        set_default_cache(original)


# --------------------------------------------------------------------------- #
# Keys
# --------------------------------------------------------------------------- #


def test_make_key_requires_namespace():
    with pytest.raises(ValueError):
        make_key("")


def test_make_key_is_deterministic():
    a = make_key("ns", 1, x=2)
    b = make_key("ns", 1, x=2)
    assert a == b


def test_make_key_orders_kwargs():
    a = make_key("ns", a=1, b=2)
    b = make_key("ns", b=2, a=1)
    assert a == b


def test_make_key_differs_for_different_parts():
    a = make_key("ns", 1)
    b = make_key("ns", 2)
    assert a != b


def test_make_key_handles_nested_dict():
    key = make_key("ns", {"b": 2, "a": 1})
    assert key.startswith("ns:")


def test_make_key_hashes_long_input():
    long_payload = {"x" * 200: "y" * 200}
    key = make_key("ns", long_payload)
    assert len(key) < 96


def test_make_key_falls_back_to_repr_for_unknown_types():
    class Foo:
        def __repr__(self):
            return "Foo()"

    key = make_key("ns", Foo())
    assert "ns:" in key


# --------------------------------------------------------------------------- #
# Decorator
# --------------------------------------------------------------------------- #


def test_cached_caches_result():
    backend = InMemoryCache()
    calls = {"n": 0}

    @cached("ns", backend=backend)
    def compute(x):
        calls["n"] += 1
        return x * 2

    assert compute(3) == 6
    assert compute(3) == 6
    assert calls["n"] == 1


def test_cached_different_args_recompute():
    backend = InMemoryCache()

    @cached("ns", backend=backend)
    def compute(x):
        return x * 2

    assert compute(1) == 2
    assert compute(2) == 4


def test_cached_ttl_expires():
    backend = InMemoryCache()

    @cached("ns", ttl=0.01, backend=backend)
    def compute(x):
        return x

    compute(1)
    time.sleep(0.02)
    # Not asserting recompute count — just that TTL passes through.
    stats_before = backend.stats()
    compute(1)
    stats_after = backend.stats()
    assert stats_after["sets"] > stats_before["sets"]


def test_cached_none_result_not_cached():
    backend = InMemoryCache()
    calls = {"n": 0}

    @cached("ns", backend=backend)
    def compute():
        calls["n"] += 1
        return None

    compute()
    compute()
    assert calls["n"] == 2


def test_cached_invalidate_removes_entry():
    backend = InMemoryCache()
    calls = {"n": 0}

    @cached("ns", backend=backend)
    def compute(x):
        calls["n"] += 1
        return x

    compute(1)
    compute.invalidate(1)  # type: ignore[attr-defined]
    compute(1)
    assert calls["n"] == 2


def test_cached_key_builder_used():
    backend = InMemoryCache()

    @cached("ns", backend=backend, key_builder=lambda *a, **kw: "constant")
    def compute(x):
        return x

    assert compute(1) == 1
    assert compute(2) == 1  # same cache key -> returns first cached value


def test_cached_exposes_cache_key_helper():
    @cached("ns")
    def compute(x):
        return x

    assert compute.cache_key(1) == compute.cache_key(1)  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Pagination
# --------------------------------------------------------------------------- #


def test_normalize_defaults():
    p = normalize_page_params(None, None)
    assert p.page == 1
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_normalize_clamps_max_size():
    p = normalize_page_params(1, MAX_PAGE_SIZE * 10)
    assert p.page_size == MAX_PAGE_SIZE


def test_normalize_rejects_negative_page():
    p = normalize_page_params(-1, 10)
    assert p.page == 1


def test_normalize_rejects_zero_size():
    p = normalize_page_params(1, 0)
    assert p.page_size == DEFAULT_PAGE_SIZE


def test_page_params_offset_and_limit():
    p = normalize_page_params(3, 10)
    assert p.offset == 20
    assert p.limit == 10


def test_paginate_sequence_returns_page():
    items, total = paginate_sequence(list(range(50)), page=2, page_size=10)
    assert items == list(range(10, 20))
    assert total == 50


def test_paginate_sequence_last_page_partial():
    items, total = paginate_sequence(list(range(23)), page=3, page_size=10)
    assert items == [20, 21, 22]
    assert total == 23


def test_paginate_sequence_out_of_range_empty():
    items, total = paginate_sequence(list(range(5)), page=10, page_size=10)
    assert items == []
    assert total == 5


def test_page_envelope_shape():
    env = page_envelope(range(10), page=1, page_size=10, total=100)
    assert env["page"] == 1
    assert env["pageSize"] == 10
    assert env["total"] == 100
    assert env["totalPages"] == 10
    assert env["hasNext"] is True
    assert env["hasPrev"] is False


def test_page_envelope_last_page():
    env = page_envelope([], page=10, page_size=10, total=100)
    assert env["hasNext"] is False
    assert env["hasPrev"] is True


def test_page_envelope_empty():
    env = page_envelope([], page=1, page_size=10, total=0)
    assert env["totalPages"] == 0
    assert env["hasNext"] is False
    assert env["hasPrev"] is False


def test_batched_yields_chunks():
    result = list(batched(range(7), 3))
    assert result == [[0, 1, 2], [3, 4, 5], [6]]


def test_batched_empty_input():
    assert list(batched([], 3)) == []


def test_batched_rejects_zero_size():
    with pytest.raises(ValueError):
        list(batched([1, 2], 0))


def test_batched_exact_multiple():
    result = list(batched(range(6), 3))
    assert result == [[0, 1, 2], [3, 4, 5]]