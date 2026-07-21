"""Campaign execution engine.

Publishes a campaign end-to-end:
- validates state and audience membership
- resolves templates per channel with language-aware fallback
- renders each recipient's message with per-recipient variables
- creates :class:`Delivery` and :class:`DeliveryRecipient` rows
- enqueues background dispatch tasks
- writes audit and status transitions
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.audience import Audience
from app.models.campaign import Campaign, CampaignAudience, CampaignTemplate
from app.models.communication import Delivery, DeliveryRecipient
from app.models.template import Template
from app.services import audit as audit_service
from app.services.template_engine import render

ALLOWED_LAUNCH_STATES = {"approved", "scheduled"}


@dataclass
class ExecutionReport:
    campaign_id: str
    channels: list[str]
    deliveries: list[str]
    recipient_count: int


def _resolve_template(db: Session, *, campaign: Campaign, channel: str, language: str) -> Template | None:
    q = (
        db.query(Template)
        .join(CampaignTemplate, CampaignTemplate.template_id == Template.id)
        .filter(CampaignTemplate.campaign_id == campaign.id, CampaignTemplate.channel == channel)
    )
    # Prefer language match; fall back to English.
    by_lang = q.filter(Template.language == language).order_by(Template.version.desc()).first()
    if by_lang:
        return by_lang
    return q.filter(Template.language == "en").order_by(Template.version.desc()).first()


def _channel_field(recipient: Audience, channel: str) -> str | None:
    if channel == "email":
        return recipient.email
    if channel in {"sms", "whatsapp", "push"}:
        return recipient.phone
    if channel == "webhook":
        return recipient.email  # webhook URL should be stored elsewhere in production
    return None


def _variables_for(recipient: Audience) -> dict[str, Any]:
    return {
        "recipient": {
            "id": str(recipient.id),
            "name": recipient.full_name,
            "email": recipient.email,
            "phone": recipient.phone,
            "language": recipient.language,
            "district": recipient.district,
            "state": recipient.state,
        },
        "name": recipient.full_name,
    }


def publish(
    db: Session, *, campaign_id: str, actor_id: uuid.UUID | None = None,
    channels: list[str] | None = None, scheduled_at: datetime | None = None,
    dispatch: bool = True,
) -> ExecutionReport:
    from app.workers.tasks import dispatch_delivery  # avoid circular import

    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise NotFoundError("Campaign not found")
    if campaign.status not in ALLOWED_LAUNCH_STATES:
        raise ConflictError(f"Campaign cannot be published from status '{campaign.status}'")

    resolved_channels = channels or list(campaign.channels or [])
    if not resolved_channels:
        raise ValidationError("Campaign has no channels configured")

    audience_ids = [
        row.audience_id for row in db.query(CampaignAudience).filter(CampaignAudience.campaign_id == campaign.id).all()
    ]
    if not audience_ids:
        raise ValidationError("Campaign has no audience members")

    recipients = db.query(Audience).filter(Audience.id.in_(audience_ids), Audience.status == "active").all()
    if not recipients:
        raise ValidationError("Campaign audience contains no active recipients")

    deliveries: list[Delivery] = []
    for channel in resolved_channels:
        delivery = Delivery(
            campaign_id=campaign.id,
            channel=channel,
            status="queued",
            scheduled_at=scheduled_at,
            attempts=0,
            priority=5,
        )
        db.add(delivery)
        db.flush()

        for recipient in recipients:
            template = _resolve_template(db, campaign=campaign, channel=channel, language=recipient.language)
            if not template:
                db.add(DeliveryRecipient(
                    delivery_id=delivery.id, audience_id=recipient.id,
                    status="failed", error_message="No template for channel/language",
                ))
                continue
            rendered, missing = render(template.body, _variables_for(recipient))
            if missing:
                db.add(DeliveryRecipient(
                    delivery_id=delivery.id, audience_id=recipient.id,
                    status="failed", error_message=f"Missing variables: {', '.join(missing)}",
                ))
                continue
            target = _channel_field(recipient, channel)
            if not target:
                db.add(DeliveryRecipient(
                    delivery_id=delivery.id, audience_id=recipient.id,
                    status="failed", error_message=f"Recipient has no {channel} address",
                ))
                continue
            db.add(DeliveryRecipient(delivery_id=delivery.id, audience_id=recipient.id, status="queued"))
        deliveries.append(delivery)

    campaign.status = "published"
    db.commit()

    audit_service.log(
        db, action="campaign_published", module="campaigns",
        actor_id=actor_id, entity_id=str(campaign.id), entity_label=campaign.name,
        metadata={"channels": resolved_channels, "recipients": len(recipients)},
    )

    if dispatch:
        for d in deliveries:
            if scheduled_at and scheduled_at > datetime.now(timezone.utc):
                eta = scheduled_at
                dispatch_delivery.apply_async(args=[str(d.id)], eta=eta)
            else:
                dispatch_delivery.apply_async(args=[str(d.id)])

    return ExecutionReport(
        campaign_id=str(campaign.id),
        channels=resolved_channels,
        deliveries=[str(d.id) for d in deliveries],
        recipient_count=len(recipients),
    )
