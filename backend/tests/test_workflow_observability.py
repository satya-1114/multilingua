"""Phase 9.3 — Observability & distributed tracing tests."""
from __future__ import annotations

import time
import uuid

import pytest

from app.observability import (
    CorrelationContext,
    InMemorySpanExporter,
    NoopSpanExporter,
    ObservabilityMetrics,
    OpenTelemetryExporter,
    SpanStatus,
    Tracer,
    build_context,
    current_correlation,
    current_span,
    default_exporter,
    default_tracer,
    from_headers,
    new_correlation_id,
    new_request_id,
    new_span_id,
    new_trace_id,
    observed,
    observability_metrics,
    require_correlation,
    reset_default_tracer,
    set_default_tracer,
    use_correlation,
)


# ─────────────────────────── Correlation ────────────────────────────


class TestCorrelation:
    def test_generated_ids_have_prefixes(self) -> None:
        assert new_correlation_id().startswith("cor_")
        assert new_request_id().startswith("req_")
        assert len(new_trace_id()) == 32  # OTEL 128-bit hex
        assert len(new_span_id()) == 16  # OTEL 64-bit hex

    def test_generated_ids_are_unique(self) -> None:
        ids = {new_correlation_id() for _ in range(50)}
        assert len(ids) == 50

    def test_build_context_fills_missing_ids(self) -> None:
        ctx = build_context()
        assert ctx.correlation_id and ctx.request_id and ctx.trace_id

    def test_build_context_preserves_supplied_ids(self) -> None:
        ctx = build_context(correlation_id="cor_test", request_id="req_test")
        assert ctx.correlation_id == "cor_test"
        assert ctx.request_id == "req_test"

    def test_use_correlation_sets_and_unsets(self) -> None:
        assert current_correlation() is None
        ctx = build_context()
        with use_correlation(ctx):
            assert current_correlation() is ctx
            assert require_correlation() is ctx
        assert current_correlation() is None

    def test_require_correlation_raises_without_context(self) -> None:
        with pytest.raises(LookupError):
            require_correlation()

    def test_context_to_dict_and_headers(self) -> None:
        ctx = build_context(workflow_id="wf1", execution_id="ex1")
        assert ctx.to_dict()["workflow_id"] == "wf1"
        headers = ctx.to_headers()
        assert headers["X-Correlation-Id"] == ctx.correlation_id
        assert headers["X-Trace-Id"] == ctx.trace_id

    def test_child_context_inherits_and_overrides(self) -> None:
        parent = build_context(workflow_id="wf1")
        child = parent.child(execution_id="ex1")
        assert child.correlation_id == parent.correlation_id
        assert child.trace_id == parent.trace_id
        assert child.workflow_id == "wf1"
        assert child.execution_id == "ex1"

    def test_from_headers_rebuilds_context(self) -> None:
        ctx = from_headers(
            {
                "X-Correlation-Id": "cor_abc",
                "X-Request-Id": "req_abc",
                "X-Trace-Id": "trc_abc",
                "X-Workflow-Id": "wf-1",
            }
        )
        assert ctx.correlation_id == "cor_abc"
        assert ctx.workflow_id == "wf-1"

    def test_from_headers_generates_defaults(self) -> None:
        ctx = from_headers({})
        assert ctx.correlation_id and ctx.request_id


# ────────────────────────────── Spans ───────────────────────────────


class TestTracer:
    def setup_method(self) -> None:
        reset_default_tracer()

    def teardown_method(self) -> None:
        reset_default_tracer()

    def test_start_span_records_to_default_exporter(self) -> None:
        tracer = default_tracer()
        with tracer.start_span("op") as span:
            assert current_span() is span
            span.set_attribute("k", "v")
        exported = default_exporter().spans()
        assert exported[-1].name == "op"
        assert exported[-1].attributes["k"] == "v"
        assert exported[-1].status == SpanStatus.OK

    def test_span_status_error_on_exception(self) -> None:
        tracer = default_tracer()
        with pytest.raises(RuntimeError):
            with tracer.start_span("boom"):
                raise RuntimeError("bad")
        span = default_exporter().spans()[-1]
        assert span.status == SpanStatus.ERROR
        assert any(e.name == "exception" for e in span.events)

    def test_nested_spans_share_trace_id_and_parent(self) -> None:
        tracer = default_tracer()
        with tracer.start_span("outer") as outer:
            with tracer.start_span("inner") as inner:
                assert inner.context.trace_id == outer.context.trace_id
                assert inner.context.parent_span_id == outer.context.span_id

    def test_current_span_none_outside(self) -> None:
        assert current_span() is None

    def test_in_memory_exporter_capacity(self) -> None:
        exporter = InMemorySpanExporter(capacity=2)
        tracer = Tracer(exporters=[exporter])
        for i in range(5):
            with tracer.start_span(f"s{i}"):
                pass
        assert len(exporter.spans()) == 2
        exporter.clear()
        assert exporter.spans() == []

    def test_noop_exporter_does_not_raise(self) -> None:
        tracer = Tracer(exporters=[NoopSpanExporter()])
        with tracer.start_span("op"):
            pass

    def test_set_default_tracer(self) -> None:
        custom = Tracer(exporters=[InMemorySpanExporter()])
        prev = set_default_tracer(custom)
        try:
            assert default_tracer() is custom
        finally:
            set_default_tracer(prev)

    def test_find_by_trace_and_attribute(self) -> None:
        exp = default_exporter()
        exp.clear()
        tracer = default_tracer()
        with tracer.start_span("a", attributes={"kind": "x"}) as a:
            trace_id = a.context.trace_id
            with tracer.start_span("b", attributes={"kind": "y"}):
                pass
        assert len(exp.find_by_trace(trace_id)) == 2
        assert [s.name for s in exp.find_by_attribute("kind", "y")] == ["b"]

    def test_trace_call_wraps_function(self) -> None:
        exp = default_exporter()
        exp.clear()
        result = default_tracer().trace_call("hello", lambda: 42)
        assert result == 42
        assert exp.spans()[-1].name == "hello"

    def test_span_add_event_and_record_exception(self) -> None:
        tracer = default_tracer()
        with tracer.start_span("s") as span:
            span.add_event("evt", attributes={"a": 1})
            span.record_exception(ValueError("x"))
        span = default_exporter().spans()[-1]
        names = [e.name for e in span.events]
        assert "evt" in names and "exception" in names

    def test_span_duration_positive(self) -> None:
        tracer = default_tracer()
        with tracer.start_span("t") as span:
            time.sleep(0.001)
        assert span.duration >= 0
        assert span.is_ended


# ─────────────────────────── observed() ─────────────────────────────


class TestObserved:
    def setup_method(self) -> None:
        reset_default_tracer()

    def teardown_method(self) -> None:
        reset_default_tracer()

    def test_observed_creates_context_and_span(self) -> None:
        with observed("op", workflow_id="wf1", execution_id="ex1") as span:
            ctx = current_correlation()
            assert ctx is not None and ctx.workflow_id == "wf1"
            assert span.attributes["workflow.id"] == "wf1"
            assert span.attributes["correlation.id"] == ctx.correlation_id

    def test_observed_uses_existing_context(self) -> None:
        outer = build_context(workflow_id="wf1")
        with use_correlation(outer):
            with observed("inner", execution_id="ex-2") as span:
                ctx = current_correlation()
                assert ctx.workflow_id == "wf1"
                assert ctx.execution_id == "ex-2"
                assert span.attributes["execution.id"] == "ex-2"

    def test_observed_records_exception(self) -> None:
        with pytest.raises(ValueError):
            with observed("op"):
                raise ValueError("nope")
        span = default_exporter().spans()[-1]
        assert span.status == SpanStatus.ERROR


# ────────────────────── ObservabilityMetrics ────────────────────────


class TestObservabilityMetrics:
    def test_leader_counters(self) -> None:
        m = ObservabilityMetrics()
        m.record_leader_elected("n1")
        m.record_leader_elected("n1")
        m.record_leader_lost("n1")
        snap = m.snapshot()
        assert snap["leaderElected"] == 2
        assert snap["leaderLost"] == 1

    def test_lock_and_queue_counters(self) -> None:
        m = ObservabilityMetrics()
        m.record_lock_acquired("k")
        m.record_lock_contended("k")
        m.record_queue_retry()
        m.record_queue_failure()
        snap = m.snapshot()
        assert snap["lockAcquired"] == 1
        assert snap["lockContended"] == 1
        assert snap["queueRetries"] == 1
        assert snap["queueFailures"] == 1

    def test_execution_throughput(self) -> None:
        m = ObservabilityMetrics()
        for _ in range(3):
            m.record_execution()
        snap = m.snapshot()
        assert snap["executionThroughput"]["count"] == 3
        assert snap["executionThroughput"]["perSecond"] >= 0

    def test_generic_counter(self) -> None:
        m = ObservabilityMetrics()
        m.counter("custom", 2)
        m.counter("custom", 3)
        snap = m.snapshot()
        assert snap["counters"]["custom"] == 5

    def test_reset_clears_state(self) -> None:
        m = ObservabilityMetrics()
        m.record_execution()
        m.reset()
        snap = m.snapshot()
        assert snap["executionThroughput"]["count"] == 0

    def test_singleton_available(self) -> None:
        observability_metrics.reset()
        observability_metrics.record_execution()
        assert observability_metrics.snapshot()["executionThroughput"]["count"] == 1
        observability_metrics.reset()


# ───────────────────── OpenTelemetry adapter ────────────────────────


class TestOpenTelemetryExporter:
    def test_falls_back_to_structured_log(self) -> None:
        # Without OTEL SDK installed the adapter must still accept spans.
        adapter = OpenTelemetryExporter()
        tracer = Tracer(exporters=[adapter])
        with tracer.start_span("op"):
            pass
        # No exception is a pass; the adapter has an internal noop path.
        adapter.shutdown()


# ─── Executor imports observability without breaking module load ────


def test_executor_module_imports_observability() -> None:
    """Regression: executor wires tracing without breaking import."""
    import importlib

    mod = importlib.import_module("app.runtime.executor")
    assert hasattr(mod, "observed")
    assert hasattr(mod, "default_tracer")