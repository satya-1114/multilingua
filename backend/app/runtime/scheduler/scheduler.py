"""Workflow scheduler (Phase 8.3).

Discovers workflow definitions whose trigger_type is ``schedule`` and
enqueues them via the configured :class:`WorkflowQueue`. No polling
loop lives here — callers (Celery beat, a periodic task, or tests)
invoke :meth:`WorkflowScheduler.tick` on their own cadence.

Schedule metadata lives *in memory* for this phase (see module-level
``_state`` on the scheduler instance) so the database schema is not
touched.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any

from sqlalchemy.orm import Session

from app.constants.workflow import TRIGGER_TYPE_SCHEDULE
from app.core.logging import get_logger
from app.models.workflow import WorkflowDefinition, WorkflowTrigger
from app.repositories.workflow import (
    workflow_definitions as _defs_repo,
    workflow_triggers as _triggers_repo,
)
from app.runtime.ha.election import default_elector
from app.runtime.ha.leader import LeaderElector

from .cron import CronValidationError, next_run_at, validate_cron
from .queue import EnqueueResult, WorkflowQueue, default_workflow_queue

log = get_logger(__name__)


@dataclass
class ScheduledRun:
    workflow_id: uuid.UUID
    trigger_id: uuid.UUID
    cron: str
    next_run_at: datetime
    enqueued: bool = False
    enqueue_result: EnqueueResult | None = None
    skipped_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkflowScheduler:
    """Discover schedule triggers and enqueue their executions."""

    def __init__(
        self,
        *,
        queue: WorkflowQueue | None = None,
        definitions_repo=_defs_repo,
        triggers_repo=_triggers_repo,
        leader: LeaderElector | None | object = ...,
        require_leader: bool = True,
    ) -> None:
        self.queue = queue or default_workflow_queue()
        self.definitions_repo = definitions_repo
        self.triggers_repo = triggers_repo
        self._last_runs: dict[str, datetime] = {}
        self._lock = RLock()
        # ``leader=...`` (Ellipsis sentinel) means "use the default elector".
        # ``leader=None`` opts out entirely (legacy / single-node dev).
        if leader is ...:
            self.leader: LeaderElector | None = default_elector()
        else:
            self.leader = leader  # type: ignore[assignment]
        self.require_leader = require_leader
        self.last_skip_reason: str | None = None

    # -- discovery -------------------------------------------------------- #

    def _has_leadership(self) -> bool:
        if not self.require_leader:
            return True
        if self.leader is None:
            return True
        return self.leader.try_acquire()

    def discover(self, db: Session) -> list[tuple[WorkflowDefinition, WorkflowTrigger]]:
        if not self._has_leadership():
            log.debug(
                "workflow.scheduler.follower_skip_discover",
                node_id=getattr(self.leader, "node_id", None),
            )
            self.last_skip_reason = "not_leader"
            return []
        definitions, _ = self.definitions_repo.list_definitions(
            db,
            trigger_type=TRIGGER_TYPE_SCHEDULE,
            enabled=True,
            page=1,
            page_size=500,
        )
        pairs: list[tuple[WorkflowDefinition, WorkflowTrigger]] = []
        for wf in definitions:
            triggers, _ = self.triggers_repo.list_triggers(
                db, workflow_definition_id=wf.id, page=1, page_size=100
            )
            for trigger in triggers:
                cron = _extract_cron(trigger)
                if cron is None:
                    continue
                if not validate_cron(cron):
                    log.warning(
                        "workflow.scheduler.invalid_cron",
                        trigger_id=str(trigger.id),
                        workflow_id=str(wf.id),
                        cron=cron,
                    )
                    continue
                pairs.append((wf, trigger))
        return pairs

    # -- execution -------------------------------------------------------- #

    def enqueue_due(
        self,
        db: Session,
        *,
        now: datetime | None = None,
        window: timedelta | None = None,
    ) -> list[ScheduledRun]:
        if not self._has_leadership():
            self.last_skip_reason = "not_leader"
            log.info(
                "workflow.scheduler.skip_not_leader",
                node_id=getattr(self.leader, "node_id", None),
            )
            return []
        self.last_skip_reason = None
        moment = now or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        window = window or timedelta(seconds=60)
        due: list[ScheduledRun] = []
        for wf, trigger in self.discover(db):
            cron = _extract_cron(trigger)
            assert cron is not None  # discover filters None
            try:
                upcoming = next_run_at(cron, now=moment - window)
            except CronValidationError as exc:
                log.warning(
                    "workflow.scheduler.cron_error",
                    trigger_id=str(trigger.id),
                    workflow_id=str(wf.id),
                    error=str(exc),
                )
                continue
            key = f"{wf.id}:{trigger.id}"
            with self._lock:
                last = self._last_runs.get(key)
            if last is not None and upcoming <= last:
                continue
            if upcoming > moment:
                continue
            run = self._enqueue(wf, trigger, cron, upcoming)
            with self._lock:
                self._last_runs[key] = upcoming
            due.append(run)
        return due

    def tick(
        self, db: Session, *, now: datetime | None = None
    ) -> list[ScheduledRun]:
        return self.enqueue_due(db, now=now)

    # -- inspection ------------------------------------------------------- #

    def peek_next_runs(
        self,
        db: Session,
        *,
        now: datetime | None = None,
        limit: int = 25,
    ) -> list[ScheduledRun]:
        moment = now or datetime.now(timezone.utc)
        runs: list[ScheduledRun] = []
        for wf, trigger in self.discover(db):
            cron = _extract_cron(trigger)
            if cron is None:
                continue
            try:
                upcoming = next_run_at(cron, now=moment)
            except CronValidationError:
                continue
            runs.append(
                ScheduledRun(
                    workflow_id=wf.id,
                    trigger_id=trigger.id,
                    cron=cron,
                    next_run_at=upcoming,
                )
            )
        runs.sort(key=lambda r: r.next_run_at)
        return runs[:limit]

    def reset(self) -> None:
        with self._lock:
            self._last_runs.clear()

    # -- helpers ---------------------------------------------------------- #

    def _enqueue(
        self,
        wf: WorkflowDefinition,
        trigger: WorkflowTrigger,
        cron: str,
        upcoming: datetime,
    ) -> ScheduledRun:
        try:
            result = self.queue.enqueue(
                wf.id,
                trigger_event=f"schedule:{trigger.event_name}",
                metadata={
                    "cron": cron,
                    "triggerId": str(trigger.id),
                    "scheduledFor": upcoming.isoformat(),
                },
            )
            log.info(
                "workflow.scheduler.enqueued",
                workflow_id=str(wf.id),
                trigger_id=str(trigger.id),
                task_id=result.task_id,
                queue=result.queue,
                cron=cron,
            )
            return ScheduledRun(
                workflow_id=wf.id,
                trigger_id=trigger.id,
                cron=cron,
                next_run_at=upcoming,
                enqueued=True,
                enqueue_result=result,
            )
        except Exception as exc:  # noqa: BLE001 — isolate one bad trigger
            log.exception(
                "workflow.scheduler.enqueue_failed",
                workflow_id=str(wf.id),
                trigger_id=str(trigger.id),
            )
            return ScheduledRun(
                workflow_id=wf.id,
                trigger_id=trigger.id,
                cron=cron,
                next_run_at=upcoming,
                enqueued=False,
                skipped_reason=str(exc),
            )


def _extract_cron(trigger: WorkflowTrigger) -> str | None:
    conditions = trigger.conditions_json or {}
    return (
        conditions.get("cron")
        or conditions.get("schedule")
        or (trigger.metadata_ or {}).get("cron")
    )


__all__ = ["ScheduledRun", "WorkflowScheduler"]
