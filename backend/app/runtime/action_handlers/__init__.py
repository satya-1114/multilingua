"""Built-in action handlers (Phase 8.1 — placeholders)."""
from __future__ import annotations

from app.runtime.action_handlers.analytics import AnalyticsHandler
from app.runtime.action_handlers.audit import AuditHandler
from app.runtime.action_handlers.notification import NotificationHandler
from app.runtime.action_handlers.update_entity import EntityUpdateHandler
from app.runtime.action_handlers.webhook import WebhookHandler

__all__ = [
    "AnalyticsHandler",
    "AuditHandler",
    "NotificationHandler",
    "EntityUpdateHandler",
    "WebhookHandler",
]
