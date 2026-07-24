from __future__ import annotations



from app.runtime.ha.leader import LeaderElector
from app.runtime.ha.locking import InMemoryLockProvider
from app.runtime.scheduler.scheduler import WorkflowScheduler


class _StubQueue:
    def __init__(self):
        self.calls = []

    def enqueue(self, workflow_id, **kw):
        self.calls.append(("enqueue", str(workflow_id), kw))
        from app.runtime.scheduler.queue import EnqueueResult
        return EnqueueResult(task_id="t", queue="q", workflow_id=str(workflow_id))

    def schedule(self, workflow_id, **kw):
        return self.enqueue(workflow_id, **kw)


class _StubDefsRepo:
    def list_definitions(self, db, **kw):
        return [], 0


class _StubTriggersRepo:
    def list_triggers(self, db, **kw):
        return [], 0


def _make(leader):
    return WorkflowScheduler(
        queue=_StubQueue(),
        definitions_repo=_StubDefsRepo(),
        triggers_repo=_StubTriggersRepo(),
        leader=leader,
    )


def test_default_leader_used_when_ellipsis_sentinel(monkeypatch):
    from app.runtime.ha import election

    provider = InMemoryLockProvider()
    stub = LeaderElector(provider=provider, ttl_s=5)
    monkeypatch.setattr(election, "_default", stub)
    s = WorkflowScheduler(
        queue=_StubQueue(),
        definitions_repo=_StubDefsRepo(),
        triggers_repo=_StubTriggersRepo(),
    )
    assert s.leader is stub


def test_none_leader_bypasses_gating():
    s = _make(None)
    assert s._has_leadership()


def test_require_leader_false_bypasses_gating():
    provider = InMemoryLockProvider()
    other = LeaderElector(provider=provider, ttl_s=5, node_id="other")
    other.try_acquire()  # our elector cannot win
    my = LeaderElector(provider=provider, ttl_s=5, node_id="me")
    s = WorkflowScheduler(
        queue=_StubQueue(),
        definitions_repo=_StubDefsRepo(),
        triggers_repo=_StubTriggersRepo(),
        leader=my,
        require_leader=False,
    )
    assert s._has_leadership()


def test_follower_skips_discover():
    provider = InMemoryLockProvider()
    other = LeaderElector(provider=provider, ttl_s=5, node_id="other")
    other.try_acquire()
    follower = LeaderElector(provider=provider, ttl_s=5, node_id="me")
    s = _make(follower)
    assert s.discover(db=None) == []
    assert s.last_skip_reason == "not_leader"


def test_follower_skips_enqueue_due():
    provider = InMemoryLockProvider()
    other = LeaderElector(provider=provider, ttl_s=5, node_id="other")
    other.try_acquire()
    follower = LeaderElector(provider=provider, ttl_s=5, node_id="me")
    s = _make(follower)
    assert s.enqueue_due(db=None) == []
    assert s.last_skip_reason == "not_leader"


def test_leader_proceeds_with_discovery():
    provider = InMemoryLockProvider()
    leader = LeaderElector(provider=provider, ttl_s=5, node_id="me")
    s = _make(leader)
    # empty repos → empty result, but no skip
    assert s.enqueue_due(db=None) == []
    assert s.last_skip_reason is None
    assert leader.is_leader


def test_leader_can_be_swapped_at_runtime():
    provider = InMemoryLockProvider()
    leader = LeaderElector(provider=provider, ttl_s=5, node_id="me")
    s = _make(leader)
    s.leader = None
    assert s._has_leadership()


def test_scheduler_records_skip_reason():
    provider = InMemoryLockProvider()
    other = LeaderElector(provider=provider, ttl_s=5, node_id="other")
    other.try_acquire()
    follower = LeaderElector(provider=provider, ttl_s=5, node_id="me")
    s = _make(follower)
    s.enqueue_due(db=None)
    assert s.last_skip_reason == "not_leader"
