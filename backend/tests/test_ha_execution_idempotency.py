from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.runtime.ha.idempotency import InMemoryIdempotencyStore
from app.runtime.result import ExecutionResult
from app.runtime.service import WorkflowRuntimeService


def _fake_executor_returning(result):
    ex = MagicMock()
    ex.execute.return_value = result
    return ex


def _mk_result(wf="wf-1"):
    now = datetime.now(timezone.utc)
    return ExecutionResult(
        workflow_id=wf,
        execution_id="ex-1",
        success=True,
        status="completed",
        started_at=now,
        completed_at=now,
    )


def test_no_idempotency_key_always_executes():
    store = InMemoryIdempotencyStore()
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=store,
    )
    svc.execute_workflow(db=None, workflow_id="wf-1")
    svc.execute_workflow(db=None, workflow_id="wf-1")
    assert svc.executor.execute.call_count == 2


def test_duplicate_execution_suppressed():
    store = InMemoryIdempotencyStore()
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=store,
    )
    md = {"idempotencyKey": "k-1"}
    first = svc.execute_workflow(db=None, workflow_id="wf-1", metadata=md)
    second = svc.execute_workflow(db=None, workflow_id="wf-1", metadata=md)
    assert svc.executor.execute.call_count == 1
    assert first.metadata.get("duplicateSuppressed") is not True
    assert second.metadata.get("duplicateSuppressed") is True


def test_duplicate_returns_success_shape():
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=InMemoryIdempotencyStore(),
    )
    md = {"idempotencyKey": "k-1"}
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata=md)
    dup = svc.execute_workflow(db=None, workflow_id="wf-1", metadata=md)
    assert dup.success is True
    assert dup.status == "completed"
    assert dup.execution_id is None


def test_different_keys_execute_independently():
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=InMemoryIdempotencyStore(),
    )
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotencyKey": "a"})
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotencyKey": "b"})
    assert svc.executor.execute.call_count == 2


def test_same_key_different_workflow_executes():
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=InMemoryIdempotencyStore(),
    )
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotencyKey": "k"})
    svc.execute_workflow(db=None, workflow_id="wf-2", metadata={"idempotencyKey": "k"})
    assert svc.executor.execute.call_count == 2


def test_snake_case_key_accepted():
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=InMemoryIdempotencyStore(),
    )
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotency_key": "k"})
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotency_key": "k"})
    assert svc.executor.execute.call_count == 1


def test_header_case_key_accepted():
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=InMemoryIdempotencyStore(),
    )
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"Idempotency-Key": "k"})
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"Idempotency-Key": "k"})
    assert svc.executor.execute.call_count == 1


def test_empty_key_ignored():
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=InMemoryIdempotencyStore(),
    )
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotencyKey": ""})
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotencyKey": ""})
    assert svc.executor.execute.call_count == 2


def test_non_string_key_ignored():
    svc = WorkflowRuntimeService(
        executor=_fake_executor_returning(_mk_result()),
        idempotency_store=InMemoryIdempotencyStore(),
    )
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotencyKey": 123})
    svc.execute_workflow(db=None, workflow_id="wf-1", metadata={"idempotencyKey": 123})
    assert svc.executor.execute.call_count == 2
