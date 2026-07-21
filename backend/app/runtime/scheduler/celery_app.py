"""Dedicated Celery application for the workflow runtime (Phase 8.3).

Isolated from the existing ``app.workers.celery_app`` module: the
workflow engine gets its own Celery instance so that queues, retry
policy, and beat schedule can evolve independently. The two apps can
share the same broker; task names are namespaced under ``workflow.*``.
"""
from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings

WORKFLOW_QUEUE_DEFAULT = "default"
WORKFLOW_QUEUE_MAIN = "workflow"
WORKFLOW_QUEUE_NOTIFICATIONS = "notifications"

WORKFLOW_QUEUES: tuple[str, ...] = (
    WORKFLOW_QUEUE_DEFAULT,
    WORKFLOW_QUEUE_MAIN,
    WORKFLOW_QUEUE_NOTIFICATIONS,
)

_exchange = Exchange("workflow", type="direct")


def _resolve_broker() -> str:
    return getattr(settings, "RABBITMQ_URL", None) or getattr(
        settings, "REDIS_URL", "memory://"
    )


def _resolve_backend() -> str:
    return getattr(settings, "REDIS_URL", "cache+memory://")


workflow_celery_app = Celery(
    "workflow",
    broker=_resolve_broker(),
    backend=_resolve_backend(),
    include=["app.runtime.scheduler.tasks"],
)

workflow_celery_app.conf.update(
    task_default_queue=WORKFLOW_QUEUE_DEFAULT,
    task_default_exchange="workflow",
    task_default_routing_key=WORKFLOW_QUEUE_DEFAULT,
    task_queues=tuple(
        Queue(name, _exchange, routing_key=name) for name in WORKFLOW_QUEUES
    ),
    task_routes={
        "workflow.execute": {"queue": WORKFLOW_QUEUE_MAIN},
        "workflow.notify": {"queue": WORKFLOW_QUEUE_NOTIFICATIONS},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
    result_expires=3600,
)


__all__ = [
    "WORKFLOW_QUEUES",
    "WORKFLOW_QUEUE_DEFAULT",
    "WORKFLOW_QUEUE_MAIN",
    "WORKFLOW_QUEUE_NOTIFICATIONS",
    "workflow_celery_app",
]
