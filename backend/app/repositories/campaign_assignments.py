from __future__ import annotations

from typing import Any, Tuple, List

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignAudience, CampaignTemplate
from app.models.audience import Audience
from app.models.template import Template
from app.core.exceptions import ValidationError, NotFoundError


def add_audience(db: Session, campaign_id: Any, audience_ids: list[str]) -> Tuple[int, int, int]:
    """Assign audience members to a campaign. Returns (added, skipped, total).

    Repository responsibilities:
    - validate existence
    - add CampaignAudience rows
    - flush before COUNT
    - update in-memory campaign.audience_count
    Do NOT commit/rollback here; router/service owns transactions.
    """
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise NotFoundError("Campaign not found")

    if campaign.status in {"published", "archived"}:
        raise ValidationError("Cannot modify audience of a published or archived campaign")

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

    # Ensure pending inserts are visible to subsequent COUNT()
    db.flush()
    total = int(db.scalar(select(func.count()).select_from(CampaignAudience).where(CampaignAudience.campaign_id == campaign.id)) or 0)
    campaign.audience_count = total
    return added, skipped, total


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
    """Remove an audience assignment. Returns (removed, total)."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise NotFoundError("Campaign not found")
    if campaign.status in {"published", "archived"}:
        raise ValidationError("Cannot modify audience of a published or archived campaign")

    link = db.scalar(
        select(CampaignAudience).where(
            CampaignAudience.campaign_id == campaign_id,
            CampaignAudience.audience_id == audience_id,
        )
    )
    if not link:
        raise NotFoundError("Assignment not found")

    db.delete(link)
    # Ensure delete is visible to COUNT()
    db.flush()
    total = int(db.scalar(select(func.count()).select_from(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)) or 0)
    campaign.audience_count = total
    return True, total


def update_audience_count(db: Session, campaign_id: Any) -> int:
    """Recompute and persist Campaign.audience_count. Returns the new count.

    This helper does not commit; callers should commit when appropriate.
    """
    # Make sure any pending writes are flushed so count is accurate
    db.flush()
    total = int(db.scalar(select(func.count()).select_from(CampaignAudience).where(CampaignAudience.campaign_id == campaign_id)) or 0)
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise NotFoundError("Campaign not found")
    campaign.audience_count = total
    return total


# Templates

def add_template(db: Session, campaign_id: Any, template_id: Any, channel: str) -> bool:
    """Assign a template to a campaign for a channel. Returns True if added.

    Repository responsibilities:
    - validate existence
    - normalize channel
    - validate template supports channel
    - insert CampaignTemplate
    - flush so callers can query newly created rows
    """
    channel_norm = (channel or "").strip().lower()
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise NotFoundError("Campaign not found")
    if campaign.status in {"published", "archived"}:
        raise ValidationError("Cannot modify templates of a published or archived campaign")
    tpl = db.get(Template, template_id)
    if not tpl:
        raise NotFoundError("Template not found")
    # Ensure template supports channel (case-insensitive, normalized)
    supported = {c.strip().lower() for c in (tpl.channels or [])}
    if channel_norm not in supported:
        raise ValidationError("Template does not support the requested channel")

    link = db.scalar(
        select(CampaignTemplate).where(
            CampaignTemplate.campaign_id == campaign.id,
            CampaignTemplate.template_id == template_id,
            CampaignTemplate.channel == channel_norm,
        )
    )
    if link is not None:
        raise ValidationError("Template assignment already exists")

    db.add(CampaignTemplate(campaign_id=campaign.id, template_id=template_id, channel=channel_norm))
    db.flush()
    return True


def list_templates(db: Session, campaign_id: Any) -> List[dict]:
    """Return list of assigned templates with metadata (templateId, channel, name, language, version, createdAt, updatedAt)."""

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
            "createdAt": tpl.created_at.isoformat() if getattr(tpl, "created_at", None) else None,
            "updatedAt": tpl.updated_at.isoformat() if getattr(tpl, "updated_at", None) else None,
        })
    return out


def remove_template(db: Session, campaign_id: Any, template_id: Any, channel: str) -> bool:
    channel_norm = (channel or "").strip().lower()
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise NotFoundError("Campaign not found")
    if campaign.status in {"published", "archived"}:
        raise ValidationError("Cannot modify templates of a published or archived campaign")

    link = db.scalar(
        select(CampaignTemplate).where(
            CampaignTemplate.campaign_id == campaign_id,
            CampaignTemplate.template_id == template_id,
            CampaignTemplate.channel == channel_norm,
        )
    )
    if not link:
        raise NotFoundError("Template assignment not found")

    db.delete(link)
    db.flush()
    return True
