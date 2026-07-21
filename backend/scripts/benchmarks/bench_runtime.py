"""Simple, non-production benchmarks for the workflow runtime.

Run with ``python -m scripts.benchmarks.bench_runtime`` from the
``backend`` directory. Output is a JSON-serializable dict of
throughput and latency numbers.
"""
from __future__ import annotations

import json
import time
from statistics import mean
from typing import Any

from app.cache import InMemoryCache
from app.cache.pagination import batched, paginate_sequence
from app.observability.metrics import ObservabilityMetrics


def bench_cache(*, iterations: int = 10_000) -> dict[str, Any]:
    cache = InMemoryCache(max_size=4096)
    write_start = time.perf_counter()
    for i in range(iterations):
        cache.set(f"k:{i}", i)
    write_elapsed = time.perf_counter() - write_start
    read_start = time.perf_counter()
    hits = 0
    for i in range(iterations):
        if cache.get(f"k:{i}") is not None:
            hits += 1
    read_elapsed = time.perf_counter() - read_start
    return {
        "iterations": iterations,
        "writeSeconds": round(write_elapsed, 6),
        "readSeconds": round(read_elapsed, 6),
        "hits": hits,
        "writesPerSecond": round(iterations / write_elapsed, 2) if write_elapsed else 0.0,
        "readsPerSecond": round(iterations / read_elapsed, 2) if read_elapsed else 0.0,
    }


def bench_metrics(*, iterations: int = 10_000) -> dict[str, Any]:
    m = ObservabilityMetrics()
    start = time.perf_counter()
    for _ in range(iterations):
        m.record_execution()
        m.record_cache_hit()
    elapsed = time.perf_counter() - start
    return {
        "iterations": iterations,
        "seconds": round(elapsed, 6),
        "opsPerSecond": round((iterations * 2) / elapsed, 2) if elapsed else 0.0,
    }


def bench_pagination(*, iterations: int = 5_000, page_size: int = 25) -> dict[str, Any]:
    data = list(range(iterations))
    latencies: list[float] = []
    for page in range(1, (iterations // page_size) + 1):
        s = time.perf_counter()
        paginate_sequence(data, page=page, page_size=page_size)
        latencies.append(time.perf_counter() - s)
    chunks = 0
    s = time.perf_counter()
    for _ in batched(data, page_size):
        chunks += 1
    batched_elapsed = time.perf_counter() - s
    return {
        "records": iterations,
        "pageSize": page_size,
        "avgPageSeconds": round(mean(latencies) if latencies else 0.0, 8),
        "batchedChunks": chunks,
        "batchedSeconds": round(batched_elapsed, 6),
    }


def bench_queue(*, iterations: int = 1_000) -> dict[str, Any]:
    # Local import — pulls in the runtime scheduler package.
    from app.runtime.scheduler.queue import InMemoryWorkflowQueue

    q = InMemoryWorkflowQueue()
    start = time.perf_counter()
    for i in range(iterations):
        q.enqueue(f"wf-{i}")
    elapsed = time.perf_counter() - start
    batch_size = 100
    batch_items = [{"workflow_id": f"batch-{i}"} for i in range(batch_size)]
    b_start = time.perf_counter()
    q.enqueue_batch(batch_items)
    b_elapsed = time.perf_counter() - b_start
    return {
        "iterations": iterations,
        "elapsedSeconds": round(elapsed, 6),
        "enqueuePerSecond": round(iterations / elapsed, 2) if elapsed else 0.0,
        "batchSize": batch_size,
        "batchSeconds": round(b_elapsed, 6),
        "depth": q.depth(),
    }


def run_all() -> dict[str, Any]:
    return {
        "cache": bench_cache(iterations=2_000),
        "metrics": bench_metrics(iterations=2_000),
        "pagination": bench_pagination(iterations=1_000, page_size=25),
        "queue": bench_queue(iterations=500),
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(run_all(), indent=2))