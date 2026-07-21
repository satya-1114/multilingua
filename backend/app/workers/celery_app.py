"""Celery configuration.

Priority queues, dead-letter routing, beat schedule, and per-task time
limits. Task modules load via `include=[...]`.
"""
from __future__ import annotations

from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings

celery_app = Celery(
    "platform",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

default_exchange = Exchange("platform", type="direct")
dlx = Exchange("platform.dlx", type="direct")

celery_app.conf.update(
    task_default_queue="default",
    task_default_exchange="platform",
    task_default_routing_key="default",
    task_queues=(
        Queue("default", default_exchange, routing_key="default"),
        Queue("ai", default_exchange, routing_key="ai",
              queue_arguments={"x-max-priority": 10, "x-dead-letter-exchange": "platform.dlx"}),
        Queue("translation", default_exchange, routing_key="translation",
              queue_arguments={"x-max-priority": 10, "x-dead-letter-exchange": "platform.dlx"}),
        Queue("delivery", default_exchange, routing_key="delivery",
              queue_arguments={"x-max-priority": 10, "x-dead-letter-exchange": "platform.dlx"}),
        Queue("delivery_high", default_exchange, routing_key="delivery_high",
              queue_arguments={"x-max-priority": 10}),
        Queue("notifications", default_exchange, routing_key="notifications",
              queue_arguments={"x-max-priority": 10}),
        Queue("analytics", default_exchange, routing_key="analytics"),
        Queue("scheduled", default_exchange, routing_key="scheduled"),
        Queue("cleanup", default_exchange, routing_key="cleanup"),
        Queue("dead_letter", dlx, routing_key="dead_letter"),
    ),
    task_routes={
        "ai.*": {"queue": "ai"},
        "translation.*": {"queue": "translation"},
        "delivery.dispatch": {"queue": "delivery"},
        "delivery.recipient": {"queue": "delivery"},
        "delivery.high_priority": {"queue": "delivery_high"},
        "notification.*": {"queue": "notifications"},
        "analytics.*": {"queue": "analytics"},
        "scheduled.*": {"queue": "scheduled"},
        "cleanup.*": {"queue": "cleanup"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=600,
    task_soft_time_limit=540,
    task_track_started=True,
    result_expires=3600,
    beat_schedule={
        "cleanup-expired-sessions": {
            "task": "cleanup.expired_sessions",
            "schedule": 3600.0,
        },
        "cleanup-expired-verification": {
            "task": "cleanup.expired_verification",
            "schedule": 3600.0,
        },
        "run-scheduled-campaigns": {
            "task": "scheduled.run_scheduled_campaigns",
            "schedule": 60.0,
        },
        "aggregate-analytics": {
            "task": "analytics.aggregate",
            "schedule": 300.0,
        },
    },
)
