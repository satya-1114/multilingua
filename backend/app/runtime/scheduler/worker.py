"""Worker bootstrap notes for the workflow Celery app (Phase 8.3).

The workflow runtime uses its own Celery application
(:data:`app.runtime.scheduler.celery_app.workflow_celery_app`). To
start a worker locally::

    celery -A app.runtime.scheduler.celery_app.workflow_celery_app \
        worker -Q workflow,default,notifications --loglevel=info

To run a beat scheduler that dispatches scheduled workflows::

    celery -A app.runtime.scheduler.celery_app.workflow_celery_app \
        beat --loglevel=info

The scheduler itself is available for programmatic use through
:class:`app.runtime.scheduler.WorkflowScheduler`.
"""
from __future__ import annotations

from .celery_app import workflow_celery_app

__all__ = ["workflow_celery_app"]
