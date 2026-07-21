from __future__ import annotations

import pytest

from app.runtime.scheduler.queue import (
    EnqueueResult,
    QueueUnavailable,
    ResilientWorkflowQueue,
    WorkflowQueue,
)


class _FlakyQueue(WorkflowQueue):
    def __init__(self, *, fail_times: int = 0, fail_forever: bool = False):
        self.calls = 0
        self.fail_times = fail_times
        self.fail_forever = fail_forever

    def enqueue(self, workflow_id, **kwargs) -> EnqueueResult:
        self.calls += 1
        if self.fail_forever or self.calls <= self.fail_times:
            raise RuntimeError("broker down")
        return EnqueueResult(task_id="t", queue="q", workflow_id=str(workflow_id))

    def schedule(self, workflow_id, *, run_at, **kwargs) -> EnqueueResult:
        return self.enqueue(workflow_id, **kwargs)


def _resilient(inner, **kw):
    kw.setdefault("sleep", lambda _s: None)
    return ResilientWorkflowQueue(inner, **kw)


def test_success_first_try_no_retry():
    inner = _FlakyQueue(fail_times=0)
    q = _resilient(inner)
    q.enqueue("wf")
    assert inner.calls == 1
    assert q.available


def test_recovers_after_transient_failure():
    inner = _FlakyQueue(fail_times=2)
    q = _resilient(inner, max_attempts=3)
    q.enqueue("wf")
    assert inner.calls == 3
    assert q.available
    assert q.stats()["successes"] == 1


def test_gives_up_after_max_attempts():
    inner = _FlakyQueue(fail_forever=True)
    q = _resilient(inner, max_attempts=2)
    with pytest.raises(QueueUnavailable):
        q.enqueue("wf")
    assert inner.calls == 2
    assert q.available is False


def test_stats_track_failures():
    inner = _FlakyQueue(fail_forever=True)
    q = _resilient(inner, max_attempts=2)
    with pytest.raises(QueueUnavailable):
        q.enqueue("wf")
    stats = q.stats()
    assert stats["failures"] == 2
    assert stats["lastError"] == "broker down"
    assert stats["backend"] == "_FlakyQueue"


def test_schedule_also_retries():
    inner = _FlakyQueue(fail_times=1)
    q = _resilient(inner, max_attempts=3)
    from datetime import datetime, timezone
    q.schedule("wf", run_at=datetime.now(timezone.utc))
    assert inner.calls == 2


def test_max_attempts_validated():
    with pytest.raises(ValueError):
        ResilientWorkflowQueue(_FlakyQueue(), max_attempts=0)


def test_is_available_true_when_no_probe():
    q = _resilient(_FlakyQueue())
    assert q.is_available()


def test_is_available_delegates_to_inner():
    class _WithProbe(_FlakyQueue):
        def is_available(self):
            return False

    q = _resilient(_WithProbe())
    assert q.is_available() is False
    assert q.available is False


def test_is_available_catches_exception():
    class _Boom(_FlakyQueue):
        def is_available(self):
            raise RuntimeError("cant reach")

    q = _resilient(_Boom())
    assert q.is_available() is False


def test_backoff_grows_exponentially():
    sleeps = []
    inner = _FlakyQueue(fail_forever=True)
    q = ResilientWorkflowQueue(
        inner, max_attempts=4, base_backoff_s=0.01, max_backoff_s=1.0,
        sleep=lambda s: sleeps.append(s),
    )
    with pytest.raises(QueueUnavailable):
        q.enqueue("wf")
    # 3 sleeps between 4 attempts, monotonic non-decreasing
    assert len(sleeps) == 3
    assert sleeps[0] <= sleeps[1] <= sleeps[2]


def test_backoff_capped():
    sleeps = []
    inner = _FlakyQueue(fail_forever=True)
    q = ResilientWorkflowQueue(
        inner, max_attempts=10, base_backoff_s=1.0, max_backoff_s=0.5,
        sleep=lambda s: sleeps.append(s),
    )
    with pytest.raises(QueueUnavailable):
        q.enqueue("wf")
    assert all(s <= 0.5 for s in sleeps)
