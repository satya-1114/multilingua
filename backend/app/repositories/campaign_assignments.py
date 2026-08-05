from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Tuple

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignAudience, CampaignTemplate
from app.models.audience import Audience
from app.models.template import Template


def add_audience(db: Session, campaign_id: Any, audience_ids: list[str]) -> Tuple[int, int]:
    """Assign audience members to a campaign. Returns (added, skipped).

    - Validates campaign exists (returns 0, len(audience_ids) if not found)
    - Validates audience exists and is not deleted
    - Ignores duplicate assignments
    - Commits transaction
    """
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return 0, len(audience_ids)

    added = 0
    skipped = 0

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

    db.commit()
    return added, skipped


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


def remove_audience(db: Session, campaign_id: Any, audience_id: Any) -> bool:
    """Remove an audience assignment. Returns True if removed."""
    link = db.scalar(
        select(CampaignAudience).where(
            CampaignAudience.campaign_id == campaign_id,
            CampaignAudience.audience_id == audience_id,
        )
    )
    if not link:
        return False
    # hard delete
    db.delete(link)
    db.commit()
    return True


def update_audience_count(db: Session, campaign_id: Any) -> int:
    """Recompute and persist Campaign.audience_count. Returns the new count."""
    total = int(db.scalar(select(func.count()).select_from(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)) or 0)
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return 0
    campaign.audience_count = total
    db.commit(); db.refresh(campaign)
    return total


# Templates

def add_template(db: Session, campaign_id: Any, template_id: Any, channel: str) -> bool:
    """Assign a template to a campaign for a channel. Returns True if added."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        return False
    tpl = db.get(Template, template_id)
    if not tpl:
        return False
    link = db.scalar(
        select(CampaignTemplate).where(
            CampaignTemplate.campaign_id == campaign.id,
            CampaignTemplate.template_id == template_id,
            CampaignTemplate.channel == channel,
        )
    )
    if link is not None:
        return False
    db.add(CampaignTemplate(campaign_id=campaign.id, template_id=template_id, channel=channel))
    db.commit()
    return True


def list_templates(db: Session, campaign_id: Any):
    """Return list of CampaignTemplate rows for a campaign."""
    stmt = select(CampaignTemplate).where(CampaignTemplate.campaign_id == campaign_id)
    return list(db.scalars(stmt))


def remove_template(db: Session, campaign_id: Any, template_id: Any, channel: str) -> bool:
    link = db.scalar(
        select(CampaignTemplate).where(
            CampaignTemplate.campaign_id == campaign_id,
            CampaignTemplate.template_id == template_id,
            CampaignTemplate.channel == channel,
        )
    )
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True
