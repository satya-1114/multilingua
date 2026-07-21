from __future__ import annotations

import pytest

from app.observability.metrics import ObservabilityMetrics


@pytest.fixture
def metrics():
    return ObservabilityMetrics()


def test_cache_hit_ratio_reported(metrics):
    metrics.record_cache_hit()
    metrics.record_cache_hit()
    metrics.record_cache_miss()
    snap = metrics.snapshot()
    assert snap["cache"]["hits"] == 2
    assert snap["cache"]["misses"] == 1
    assert snap["cache"]["hitRatio"] == pytest.approx(2 / 3, rel=1e-3)
    assert snap["cache"]["missRatio"] == pytest.approx(1 / 3, rel=1e-3)


def test_cache_ratios_zero_when_empty(metrics):
    snap = metrics.snapshot()
    assert snap["cache"]["hitRatio"] == 0.0
    assert snap["cache"]["missRatio"] == 0.0


def test_db_queries_counter(metrics):
    metrics.record_db_queries(3)
    metrics.record_db_queries()
    assert metrics.snapshot()["dbQueries"] == 4


def test_response_time_average(metrics):
    metrics.record_response_time(0.1)
    metrics.record_response_time(0.2)
    metrics.record_response_time(0.3)
    assert metrics.snapshot()["avgResponseTime"] == pytest.approx(0.2, rel=1e-3)


def test_response_time_zero_when_empty(metrics):
    assert metrics.snapshot()["avgResponseTime"] == 0.0


def test_response_time_ignores_negative(metrics):
    metrics.record_response_time(-1.0)
    assert metrics.snapshot()["avgResponseTime"] == 0.0


def test_batch_enqueue_tracked(metrics):
    metrics.record_batch_enqueue(10)
    metrics.record_batch_enqueue(5)
    assert metrics.snapshot()["batchEnqueues"] == 15


def test_queue_depth_recorded(metrics):
    metrics.record_queue_depth(5, capacity=10)
    snap = metrics.snapshot()
    assert snap["queueUtilization"]["depth"] == 5
    assert snap["queueUtilization"]["capacity"] == 10
    assert snap["queueUtilization"]["ratio"] == 0.5


def test_queue_utilization_zero_without_capacity(metrics):
    metrics.record_queue_depth(5)
    snap = metrics.snapshot()
    assert snap["queueUtilization"]["ratio"] == 0.0


def test_queue_utilization_capped(metrics):
    metrics.record_queue_depth(500, capacity=10)
    assert metrics.snapshot()["queueUtilization"]["ratio"] == 1.0


def test_reset_clears_perf_metrics(metrics):
    metrics.record_cache_hit()
    metrics.record_db_queries(5)
    metrics.record_response_time(0.4)
    metrics.record_batch_enqueue(3)
    metrics.record_queue_depth(2, capacity=4)
    metrics.reset()
    snap = metrics.snapshot()
    assert snap["cache"]["hits"] == 0
    assert snap["dbQueries"] == 0
    assert snap["avgResponseTime"] == 0.0
    assert snap["batchEnqueues"] == 0
    assert snap["queueUtilization"]["depth"] == 0


def test_free_form_counter_still_works(metrics):
    metrics.counter("custom", 2)
    metrics.counter("custom")
    assert metrics.snapshot()["counters"]["custom"] == 3


def test_snapshot_keys_present(metrics):
    snap = metrics.snapshot()
    for key in (
        "cache",
        "dbQueries",
        "avgResponseTime",
        "batchEnqueues",
        "queueUtilization",
    ):
        assert key in snap


def test_snapshot_independent_of_reset_between_recordings(metrics):
    metrics.record_cache_hit()
    metrics.snapshot()
    metrics.record_cache_hit()
    assert metrics.snapshot()["cache"]["hits"] == 2


def test_multiple_metrics_isolated():
    a = ObservabilityMetrics()
    b = ObservabilityMetrics()
    a.record_cache_hit()
    assert b.snapshot()["cache"]["hits"] == 0


def test_record_batch_enqueue_zero(metrics):
    metrics.record_batch_enqueue(0)
    assert metrics.snapshot()["batchEnqueues"] == 0


def test_record_queue_depth_negative_clamped(metrics):
    metrics.record_queue_depth(-5, capacity=-2)
    snap = metrics.snapshot()
    assert snap["queueUtilization"]["depth"] == 0
    assert snap["queueUtilization"]["capacity"] == 0


def test_response_time_bounded_window(metrics):
    for i in range(2000):
        metrics.record_response_time(0.001)
    # Deque maxlen keeps latest 1024
    snap = metrics.snapshot()
    assert snap["avgResponseTime"] > 0


def test_cache_hit_and_miss_default_amount(metrics):
    metrics.record_cache_hit()
    metrics.record_cache_miss()
    snap = metrics.snapshot()
    assert snap["cache"]["hits"] == 1
    assert snap["cache"]["misses"] == 1