from __future__ import annotations

from scripts.benchmarks.bench_runtime import (
    bench_cache,
    bench_metrics,
    bench_pagination,
    bench_queue,
    run_all,
)


def test_bench_cache_returns_shape():
    result = bench_cache(iterations=100)
    assert result["iterations"] == 100
    assert result["hits"] == 100
    assert result["writesPerSecond"] >= 0
    assert result["readsPerSecond"] >= 0


def test_bench_metrics_positive_throughput():
    result = bench_metrics(iterations=100)
    assert result["iterations"] == 100
    assert result["opsPerSecond"] > 0


def test_bench_pagination_returns_chunks():
    result = bench_pagination(iterations=100, page_size=10)
    assert result["records"] == 100
    assert result["pageSize"] == 10
    assert result["batchedChunks"] == 10


def test_bench_queue_records_enqueue_rate():
    result = bench_queue(iterations=50)
    assert result["iterations"] == 50
    assert result["depth"] == 50 + result["batchSize"]
    assert result["enqueuePerSecond"] > 0


def test_run_all_reports_every_section():
    result = run_all()
    for section in ("cache", "metrics", "pagination", "queue"):
        assert section in result


def test_bench_cache_small_iterations_ok():
    result = bench_cache(iterations=1)
    assert result["iterations"] == 1
    assert result["hits"] == 1


def test_bench_metrics_small_iterations_ok():
    result = bench_metrics(iterations=1)
    assert result["iterations"] == 1


def test_bench_pagination_small_iterations_ok():
    result = bench_pagination(iterations=25, page_size=5)
    assert result["batchedChunks"] == 5


def test_bench_queue_small_iterations_ok():
    result = bench_queue(iterations=1)
    assert result["iterations"] == 1