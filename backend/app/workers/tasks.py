"""Celery task registry.

Tasks are named with a queue-prefixed convention so :mod:`celery_app`
routing rules can dispatch them. Retries use exponential backoff with jitter
and log failures to the dead-letter queue.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from celery.exceptions import MaxRetriesExceededError

from app.core.logging import get_logger
from app.database.session import SessionLocal
from app.models.audience import Audience
from app.models.campaign import Campaign
from app.models.communication import Delivery, DeliveryRecipient
from app.models.notification import Notification
from app.models.template import Template
from app.services import ai as ai_service
from app.services import communication as comm
from app.services import translation as tr
from app.services.template_engine import render
from app.workers.celery_app import celery_app

log = get_logger(__name__)


def _backoff(attempt: int, *, base: int = 5, cap: int = 900) -> int:
    """Exponential backoff with jitter (seconds)."""
    delay = min(cap, base * (2 ** attempt))
    return int(delay * random.uniform(0.5, 1.5))


def _record_dead_letter(task_name: str, payload: dict, error: str) -> None:
    log.error("task_dead_letter", task=task_name, payload=payload, error=error)


# --------------------------------------------------------------- AI + Translation


@celery_app.task(name="ai.generate_content", bind=True, max_retries=3, acks_late=True)
def generate_content(self, prompt: str, mode: str = "generate", tone: str | None = None, language: str = "en") -> dict:
    try:
        return asyncio.run(ai_service.generate(prompt=prompt, mode=mode, tone=tone, language=language))
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=_backoff(self.request.retries))
        except MaxRetriesExceededError:
            _record_dead_letter("ai.generate_content", {"prompt": prompt, "mode": mode}, str(exc))
            raise


@celery_app.task(name="translation.translate", bind=True, max_retries=3, acks_late=True)
def translate_task(self, text: str, target_language: str, source_language: str | None = None) -> dict:
    try:
        return asyncio.run(tr.translate(text=text, target_language=target_language, source_language=source_language))
    except Exception as exc:
        try:
            raise self.retry(exc=exc, countdown=_backoff(self.request.retries))
        except MaxRetriesExceededError:
            _record_dead_letter("translation.translate", {"target": target_language}, str(exc))
            raise


@celery_app.task(name="translation.batch", bind=True, max_retries=2, acks_late=True)
def translate_batch(self, items: list[str], target_language: str) -> list[dict]:
    try:
        return asyncio.run(tr.translate_batch(items=items, target_language=target_language))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_backoff(self.request.retries))


# --------------------------------------------------------------- Delivery


def _render_for(recipient: Audience, template: Template) -> str:
    body, _ = render(template.body, {
        "recipient": {
            "name": recipient.full_name, "email": recipient.email, "phone": recipient.phone,
            "language": recipient.language, "district": recipient.district, "state": recipient.state,
        },
        "name": recipient.full_name,
    })
    return body


@celery_app.task(name="delivery.dispatch", bind=True, max_retries=5, acks_late=True)
def dispatch_delivery(self, delivery_id: str) -> dict:
    db = SessionLocal()
    try:
        delivery = db.get(Delivery, delivery_id)
        if not delivery:
            return {"status": "missing"}
        delivery.status = "processing"
        delivery.attempts += 1
        db.commit()

        recipients = (
            db.query(DeliveryRecipient)
            .filter(DeliveryRecipient.delivery_id == delivery.id, DeliveryRecipient.status == "queued")
            .all()
        )
        total = len(recipients)
        sent = failed = 0
        for r in recipients:
            deliver_recipient.apply_async(args=[str(r.id)])
            sent += 1

        delivery.status = "dispatched"
        db.commit()
        return {"status": "dispatched", "recipients": total, "queued": sent, "failed": failed}
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc, countdown=_backoff(self.request.retries))
        except MaxRetriesExceededError:
            _record_dead_letter("delivery.dispatch", {"delivery_id": delivery_id}, str(exc))
            raise
    finally:
        db.close()


@celery_app.task(name="delivery.recipient", bind=True, max_retries=5, acks_late=True)
def deliver_recipient(self, recipient_id: str) -> dict:
    db = SessionLocal()
    try:
        recipient_row = db.get(DeliveryRecipient, recipient_id)
        if not recipient_row:
            return {"status": "missing"}
        delivery = db.get(Delivery, recipient_row.delivery_id)
        audience = db.get(Audience, recipient_row.audience_id)
        if not delivery or not audience:
            recipient_row.status = "failed"
            recipient_row.error_message = "missing_delivery_or_audience"
            db.commit()
            return {"status": "failed"}

        # Locate template — first template matching campaign, channel, language.
        template = _lookup_template(db, campaign_id=delivery.campaign_id, channel=delivery.channel, language=audience.language)
        if not template:
            recipient_row.status = "failed"
            recipient_row.error_message = "template_missing"
            db.commit()
            return {"status": "failed"}
        body = _render_for(audience, template)

        channel = delivery.channel
        if channel == "email":
            result = comm.send_email(to=audience.email or "", subject="Update from your organization", body=body)
        elif channel == "sms":
            result = comm.send_sms(to=audience.phone or "", body=body)
        elif channel == "whatsapp":
            result = comm.send_whatsapp(to=audience.phone or "", body=body)
        elif channel == "push":
            result = comm.send_push(to=audience.phone or "", title="Notification", body=body)
        elif channel == "webhook":
            result = comm.send_webhook(url=audience.email or "", body=body)
        else:
            recipient_row.status = "failed"
            recipient_row.error_message = f"unsupported_channel:{channel}"
            db.commit()
            return {"status": "failed"}

        if result["status"] == "sent":
            recipient_row.status = "delivered"
            recipient_row.delivered_at = datetime.now(timezone.utc)
        elif result["status"] == "skipped":
            recipient_row.status = "skipped"
            recipient_row.error_message = result.get("errorCode") or "skipped"
        else:
            recipient_row.status = "failed"
            recipient_row.error_message = (result.get("errorMessage") or "")[:500]
            db.commit()
            # Retry on transient failures.
            try:
                raise self.retry(countdown=_backoff(self.request.retries))
            except MaxRetriesExceededError:
                _record_dead_letter("delivery.recipient", {"recipient_id": recipient_id}, recipient_row.error_message or "")
                return {"status": "failed"}
        db.commit()
        return {"status": recipient_row.status, "provider": result.get("provider")}
    finally:
        db.close()


def _lookup_template(db, *, campaign_id, channel, language):
    from app.models.campaign import CampaignTemplate
    q = (
        db.query(Template)
        .join(CampaignTemplate, CampaignTemplate.template_id == Template.id)
        .filter(CampaignTemplate.campaign_id == campaign_id, CampaignTemplate.channel == channel)
    )
    match = q.filter(Template.language == language).order_by(Template.version.desc()).first()
    return match or q.filter(Template.language == "en").order_by(Template.version.desc()).first()


# --------------------------------------------------------------- Notifications


@celery_app.task(name="notification.dispatch", bind=True, max_retries=3, acks_late=True)
def dispatch_notification(self, notification_id: str) -> dict:
    db = SessionLocal()
    try:
        n = db.get(Notification, notification_id)
        if not n:
            return {"status": "missing"}
        # In-app notifications are already persisted; nothing to do here beyond marking dispatched.
        return {"status": "delivered", "id": notification_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=_backoff(self.request.retries))
    finally:
        db.close()


# --------------------------------------------------------------- Scheduled + cleanup


@celery_app.task(name="scheduled.run_scheduled_campaigns")
def run_scheduled_campaigns() -> dict:
    from app.services.campaign_execution import publish as publish_campaign

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(Campaign)
            .filter(Campaign.status == "scheduled", Campaign.starts_at.isnot(None), Campaign.starts_at <= now)
            .all()
        )
        launched = []
        for c in due:
            try:
                report = publish_campaign(db, campaign_id=str(c.id))
                launched.append(report.campaign_id)
            except Exception as exc:
                log.error("scheduled_launch_failed", campaign_id=str(c.id), error=str(exc))
        return {"launched": launched}
    finally:
        db.close()


@celery_app.task(name="cleanup.expired_sessions")
def cleanup_expired_sessions() -> int:
    from app.models.user import Session as SessionModel
    db = SessionLocal()
    try:
        deleted = db.query(SessionModel).filter(SessionModel.expires_at < datetime.now(timezone.utc)).delete()
        db.commit()
        return deleted
    finally:
        db.close()


@celery_app.task(name="cleanup.expired_verification")
def cleanup_expired_verification() -> int:
    from app.services.security_center import cleanup_expired_verification as _cleanup
    db = SessionLocal()
    try:
        return _cleanup(db)
    finally:
        db.close()


@celery_app.task(name="analytics.aggregate")
def aggregate_analytics() -> dict:
    log.info("analytics_aggregate_tick")
    return {"ok": True, "at": datetime.now(timezone.utc).isoformat()}


# Backwards compatibility aliases (import surface used elsewhere).
dispatch = dispatch_delivery
translate = translate_task
