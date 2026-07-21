from __future__ import annotations

import pytest

from app.runtime.scheduler.queue import InMemoryWorkflowQueue


def test_enqueue_batch_records_all():
    q = InMemoryWorkflowQueue()
    items = [{"workflow_id": f"wf-{i}"} for i in range(5)]
    results = q.enqueue_batch(items)
    assert len(results) == 5
    assert q.depth() == 5


def test_enqueue_batch_returns_result_per_item():
    q = InMemoryWorkflowQueue()
    items = [{"workflow_id": "a"}, {"workflow_id": "b"}]
    results = q.enqueue_batch(items)
    workflows = {r.workflow_id for r in results}
    assert workflows == {"a", "b"}


def test_enqueue_batch_forwards_metadata():
    q = InMemoryWorkflowQueue()
    items = [{"workflow_id": "a", "metadata": {"batch": 1}}]
    results = q.enqueue_batch(items)
    assert results[0].metadata == {"batch": 1}


def test_enqueue_batch_requires_workflow_id():
    q = InMemoryWorkflowQueue()
    with pytest.raises(ValueError):
        q.enqueue_batch([{"payload": {}}])


def test_enqueue_batch_empty_returns_empty():
    q = InMemoryWorkflowQueue()
    assert q.enqueue_batch([]) == []


def test_depth_reflects_total_size():
    q = InMemoryWorkflowQueue()
    q.enqueue("a")
    q.enqueue("b")
    assert q.depth() == 2


def test_depth_filters_by_queue():
    q = InMemoryWorkflowQueue()
    q.enqueue("a")
    q.enqueue("b")
    from app.runtime.scheduler.celery_app import WORKFLOW_QUEUE_MAIN

    assert q.depth(queue=WORKFLOW_QUEUE_MAIN) == 2


def test_depth_zero_for_unknown_queue():
    q = InMemoryWorkflowQueue()
    q.enqueue("a")
    assert q.depth(queue="does-not-exist") == 0


def test_depth_by_queue_groups_counts():
    q = InMemoryWorkflowQueue()
    q.enqueue("a")
    q.enqueue("b")
    grouped = q.depth_by_queue()
    assert sum(grouped.values()) == 2


def test_utilization_zero_when_no_capacity():
    q = InMemoryWorkflowQueue()
    assert q.utilization(capacity=0) == 0.0


def test_utilization_ratio():
    q = InMemoryWorkflowQueue()
    for i in range(5):
        q.enqueue(f"wf-{i}")
    assert q.utilization(capacity=10) == 0.5


def test_utilization_capped_at_one():
    q = InMemoryWorkflowQueue()
    for i in range(20):
        q.enqueue(f"wf-{i}")
    assert q.utilization(capacity=10) == 1.0


def test_enqueue_count_tracks_total():
    q = InMemoryWorkflowQueue()
    q.enqueue("a")
    q.enqueue("b")
    q.clear()
    q.enqueue("c")
    assert q.enqueue_count() == 3


def test_clear_resets_depth_only():
    q = InMemoryWorkflowQueue()
    q.enqueue("a")
    q.clear()
    assert q.depth() == 0
    assert q.enqueue_count() == 1


def test_enqueue_batch_bumps_enqueue_count():
    q = InMemoryWorkflowQueue()
    q.enqueue_batch([{"workflow_id": "a"}, {"workflow_id": "b"}])
    assert q.enqueue_count() == 2