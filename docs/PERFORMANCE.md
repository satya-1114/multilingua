# Performance

Baseline results for the runtime, cache, pagination, and queue primitives
introduced in Phase 9.4. All numbers are produced by the benchmark harness
at `backend/scripts/benchmarks/bench_runtime.py`.

## Methodology

- Pure in-process benchmarks; no network, no database.
- Each benchmark reports iteration count and derived rate (ops/sec).
- Numbers are indicative, not SLOs. Re-run per environment before quoting.

```
cd backend
python -m scripts.benchmarks.bench_runtime
```

## Hardware assumptions

- Reference: 4 vCPU, 8 GB RAM Linux container, Python 3.12.
- CI runs on smaller hardware; expect ~50–70% of local numbers.

## Baseline (reference hardware)

| Suite | Metric | Typical range |
| --- | --- | --- |
| Cache writes | ops/sec | 1.0M – 2.5M |
| Cache reads | ops/sec | 1.5M – 3.0M |
| Metrics recording | ops/sec | 2.0M – 4.0M |
| Pagination window | avg seconds/page | < 1e-5 |
| Queue enqueue (in-memory) | enqueues/sec | 200k – 400k |

Absolute values shift with hardware; the meaningful signal is
**relative change** across releases.

## Tuning recommendations

- **Cache**: raise `max_size` on `InMemoryCache` when `evictions` grows
  faster than `sets` in `observability_metrics`. Enable TTLs on
  volatile data only.
- **Pagination**: keep `page_size` ≤ 100 for API responses; use
  `batched()` for bulk producers to avoid unbounded lists.
- **Queue**: prefer `enqueue_batch` for fan-out from a single trigger;
  it reduces per-item lock overhead. Sample queue depth into
  `observability_metrics.record_queue_depth(...)` to feed dashboards.
- **Runtime**: handler instances are reused. Avoid registering new
  handlers on hot paths — do it once at startup.
- **Backend workers**: set `WORKER_CONCURRENCY` between (vCPU × 2)
  and (vCPU × 4) for I/O-bound handlers; lower for CPU-bound.

## Where results live

- Executable harness: `backend/scripts/benchmarks/bench_runtime.py`
- Sanity tests: `backend/tests/test_benchmarks.py`
- Runtime metrics (live): `GET /v1/runtime/observability/metrics`