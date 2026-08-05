from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Tuple, List

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignAudience, CampaignTemplate
from app.models.audience import Audience
from app.models.template import Template
from app.core.exceptions import ValidationError


def add_audience(db: Session, campaign_id: Any, audience_ids: list[str]) -> Tuple[int, int, int]:
    """Assign audience members to a campaign. Returns (added, skipped, new_count).

    Performs validation and writes within a single transaction. Rolls back on failure.
    Prevents assignment when campaign is published or archived.
    """
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return 0, len(audience_ids), 0

    if campaign.status in {"published", "archived"}:
        raise ValidationError("Cannot modify audience of a published or archived campaign")

    added = 0
    skipped = 0

    # Use a transactional block to ensure single commit/rollback
    with db.begin():
        for audience_id in dict.fromkeys(audience_ids):
            aud = db.scalar(select(Audience).where(Audience.id == audience_id, Audience.deleted_at.is_(None)))
            if not aud:
                skipped += 1
                continue

            link = db.scalar(
                select(CampaignAudience).where(
                    CampaignAudience.campaign_id == campaign.id,
                    CampaignAudience.audience_id == audience_id,
                )
            )
            if link is None:
                db.add(CampaignAudience(campaign_id=campaign.id, audience_id=audience_id))
                added += 1
            else:
                skipped += 1

        # Recompute and persist audience_count in same transaction
        total = int(db.scalar(select(func.count()).select_from(CampaignAudience).where(CampaignAudience.campaign_id == campaign.id)) or 0)
        campaign.audience_count = total
        # No explicit commit here; context manager will commit
    return added, skipped, campaign.audience_count


def list_audience(db: Session, campaign_id: Any, *, page: int = 1, page_size: int = 25, search: str | None = None):
    """Return (items: list[Audience], total: int) for campaign audience."""
    from sqlalchemy import or_, desc

    stmt = select(Audience).join(CampaignAudience, CampaignAudience.audience_id == Audience.id).where(
        CampaignAudience.campaign_id == campaign_id,
        Audience.deleted_at.is_(None),
    )
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Audience.full_name.ilike(like), Audience.email.ilike(like), Audience.phone.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(desc(Audience.created_at)).offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(stmt)), int(total)


def remove_audience(db: Session, campaign_id: Any, audience_id: Any) -> Tuple[bool, int]:
    """Remove an audience assignment. Returns (removed, new_count)."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return False, 0
    if campaign.status in {"published", "archived"}:
        raise ValidationError("Cannot modify audience of a published or archived campaign")

    with db.begin():
        link = db.scalar(
            select(CampaignAudience).where(
                CampaignAudience.campaign_id == campaign_id,
                CampaignAudience.audience_id == audience_id,
            )
        )
        if not link:
            return False, int(db.scalar(select(func.count()).select_from(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)) or 0)
        db.delete(link)
        total = int(db.scalar(select(func.count()).select_from(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)) or 0)
        campaign.audience_count = total
    return True, campaign.audience_count


def update_audience_count(db: Session, campaign_id: Any) -> int:
    """Recompute and persist Campaign.audience_count. Returns the new count.

    This helper does not commit; callers can use it inside a transaction or rely on repo methods
    that already update the count.
    """
    total = int(db.scalar(select(func.count()).select_from(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)) or 0)
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return 0
    campaign.audience_count = total
    db.refresh(campaign)
    return total


# Templates

def add_template(db: Session, campaign_id: Any, template_id: Any, channel: str) -> bool:
    """Assign a template to a campaign for a channel. Returns True if added.

    - Normalizes channel to lowercase
    - Validates campaign and template exist
    - Validates template supports the channel
    - Prevents assignment to published/archived campaigns
    - Uses single transaction
    """
    channel_norm = (channel or "").lower()
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return False
    if campaign.status in {"published", "archived"}:
        raise ValidationError("Cannot modify templates of a published or archived campaign")
    tpl = db.get(Template, template_id)
    if not tpl:
        return False
    # Ensure template supports channel (case-insensitive)
    supported = [c.lower() for c in (tpl.channels or [])]
    if channel_norm not in supported:
        raise ValidationError("Template does not support the requested channel")

    with db.begin():
        link = db.scalar(
            select(CampaignTemplate).where(
                CampaignTemplate.campaign_id == campaign.id,
                CampaignTemplate.template_id == template_id,
                CampaignTemplate.channel == channel_norm,
            )
        )
        if link is not None:
            return False
        db.add(CampaignTemplate(campaign_id=campaign.id, template_id=template_id, channel=channel_norm))
    return True


def list_templates(db: Session, campaign_id: Any) -> List[dict]:
    """Return list of assigned templates with metadata (templateId, channel, name, language, version)."""
    from sqlalchemy import join

    stmt = select(CampaignTemplate, Template).join(Template, Template.id == CampaignTemplate.template_id).where(
        CampaignTemplate.campaign_id == campaign_id
    )
    rows = db.execute(stmt).all()
    out: List[dict] = []
    for ct, tpl in rows:
        out.append({
            "templateId": str(ct.template_id),
            "channel": ct.channel,
            "name": tpl.name,
            "language": tpl.language,
            "version": tpl.version,
        })
    return out


def remove_template(db: Session, campaign_id: Any, template_id: Any, channel: str) -> bool:
    channel_norm = (channel or "").lower()
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return False
    if campaign.status in {"published", "archived"}:
        raise ValidationError("Cannot modify templates of a published or archived campaign")

    with db.begin():
        link = db.scalar(
            select(CampaignTemplate).where(
                CampaignTemplate.campaign_id == campaign_id,
                CampaignTemplate.template_id == template_id,
                CampaignTemplate.channel == channel_norm,
            )
        )
        if not link:
            return False
        db.delete(link)
    return True
