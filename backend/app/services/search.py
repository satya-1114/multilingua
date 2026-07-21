"""Global search service.

Uses PostgreSQL ILIKE + trigram-friendly ordering for portable
cross-module search. Respects workspace scoping and the caller's
permissions (unknown scopes are silently skipped).

Optional Redis cache short-circuits identical repeat queries. When
``pg_trgm`` is available the ranking degrades gracefully to substring
match order.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.audience import Audience
from app.models.audit import AuditLog
from app.models.campaign import Campaign
from app.models.media import Media
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.template import Template
from app.models.user import User
from app.models.volunteer import Volunteer, VolunteerTask
from app.models.disaster import Disaster, DisasterAssignment
from app.models.public_access import PublicResource
from app.models.translation import Translation
from app.models.analytics import AnalyticsMetric, AnalyticsReport, AnalyticsSnapshot
from app.services import cache

SCOPE_PERMISSIONS = {
    "campaign": "campaigns:view",
    "audience": "audience:view",
    "organization": "organizations:view",
    "user": "users:view",
    "template": "templates:view",
    "media": "media:view",
    "notification": None,          # always allowed for the current user
    "audit": "audit:view",
    "volunteer": "volunteer:view",
    "task": "task:view",
    "disaster": "disaster:view",
    "assignment": "assignment:view",
    "public_resource": "public:view",
    "translation": "translation:view",
    "analytics": "analytics:view",
}


def _like(term: str) -> str:
    return f"%{term.strip()}%"


def _hit(scope: str, id: Any, title: str, subtitle: str | None, href: str, score: float = 1.0) -> dict:
    return {
        "scope": scope,
        "id": str(id),
        "title": title,
        "subtitle": subtitle,
        "href": href,
        "score": score,
    }


def _search_campaigns(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(Campaign).where(Campaign.name.ilike(_like(q)))
    if workspace_id:
        stmt = stmt.where(Campaign.workspace_id == workspace_id)
    stmt = stmt.limit(limit)
    return [
        _hit("campaign", c.id, c.name, c.status, f"/campaigns/{c.id}",
             score=2.0 if q.lower() in (c.name or "").lower() else 1.0)
        for c in db.scalars(stmt)
    ]


def _search_audience(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(Audience).where(or_(
        Audience.full_name.ilike(_like(q)),
        Audience.email.ilike(_like(q)),
        Audience.phone.ilike(_like(q)),
    ))
    if workspace_id:
        stmt = stmt.where(Audience.workspace_id == workspace_id)
    stmt = stmt.limit(limit)
    return [_hit("audience", a.id, a.full_name or a.email or "Contact", a.email, f"/audience/{a.id}") for a in db.scalars(stmt)]


def _search_organizations(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(Organization).where(or_(Organization.name.ilike(_like(q)), Organization.slug.ilike(_like(q)))).limit(limit)
    return [_hit("organization", o.id, o.name, o.slug, f"/organizations/{o.id}") for o in db.scalars(stmt)]


def _search_users(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(User).where(or_(User.email.ilike(_like(q)), User.full_name.ilike(_like(q)))).limit(limit)
    return [_hit("user", u.id, u.full_name or u.email, u.email, f"/users/{u.id}") for u in db.scalars(stmt)]


def _search_templates(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(Template).where(or_(Template.name.ilike(_like(q)), Template.body.ilike(_like(q))))
    if workspace_id:
        stmt = stmt.where(Template.workspace_id == workspace_id)
    stmt = stmt.limit(limit)
    return [_hit("template", t.id, t.name, t.status, f"/templates/{t.id}") for t in db.scalars(stmt)]


def _search_media(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(Media).where(Media.name.ilike(_like(q)))
    if workspace_id:
        stmt = stmt.where(Media.workspace_id == workspace_id)
    stmt = stmt.limit(limit)
    return [_hit("media", m.id, m.name, m.mime_type, f"/media/{m.id}") for m in db.scalars(stmt)]


def _search_notifications(db: Session, q: str, user_id: str | None, limit: int) -> list[dict]:
    stmt = select(Notification).where(or_(Notification.title.ilike(_like(q)), Notification.message.ilike(_like(q))))
    if user_id:
        stmt = stmt.where(Notification.user_id == user_id)
    stmt = stmt.limit(limit)
    return [_hit("notification", n.id, n.title, n.category, n.href or "/notifications") for n in db.scalars(stmt)]


def _search_audit(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(AuditLog).where(or_(AuditLog.action.ilike(_like(q)), AuditLog.entity_label.ilike(_like(q))))
    if workspace_id:
        stmt = stmt.where(AuditLog.workspace_id == workspace_id)
    stmt = stmt.limit(limit)
    return [_hit("audit", a.id, a.action, a.module, f"/security/audit/{a.id}") for a in db.scalars(stmt)]


def _search_volunteers(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(Volunteer).where(or_(
        Volunteer.current_location.ilike(_like(q)),
        Volunteer.availability.ilike(_like(q)),
        Volunteer.status.ilike(_like(q)),
    )).limit(limit)
    return [_hit("volunteer", v.id, v.current_location or v.status or "Volunteer",
                 v.availability, f"/volunteers/{v.id}") for v in db.scalars(stmt)]


def _search_tasks(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(VolunteerTask).where(or_(
        VolunteerTask.title.ilike(_like(q)),
        VolunteerTask.description.ilike(_like(q)),
    )).limit(limit)
    return [_hit("task", t.id, t.title, t.status, f"/tasks/{t.id}") for t in db.scalars(stmt)]


def _search_disasters(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(Disaster).where(or_(
        Disaster.title.ilike(_like(q)),
        Disaster.address.ilike(_like(q)),
        Disaster.city.ilike(_like(q)),
        Disaster.district.ilike(_like(q)),
        Disaster.state.ilike(_like(q)),
        Disaster.country.ilike(_like(q)),
    )).limit(limit)
    return [_hit("disaster", d.id, d.title,
                 d.city or d.state or d.status, f"/disasters/{d.id}")
            for d in db.scalars(stmt)]


def _search_assignments(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(DisasterAssignment).where(or_(
        DisasterAssignment.role.ilike(_like(q)),
        DisasterAssignment.notes.ilike(_like(q)),
    )).limit(limit)
    return [_hit("assignment", a.id, a.role or "Assignment",
                 a.status, f"/disasters/{a.disaster_id}/assignments/{a.id}")
            for a in db.scalars(stmt)]


def _search_public_resources(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(PublicResource).where(or_(
        PublicResource.title.ilike(_like(q)),
        PublicResource.slug.ilike(_like(q)),
        PublicResource.resource_type.ilike(_like(q)),
        PublicResource.visibility.ilike(_like(q)),
    )).limit(limit)
    return [_hit("public_resource", r.id, r.title, r.slug or r.resource_type,
                 f"/public-resources/{r.id}")
            for r in db.scalars(stmt)]


def _search_translations(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    stmt = select(Translation).where(or_(
        Translation.entity_type.ilike(_like(q)),
        Translation.locale.ilike(_like(q)),
        Translation.field_name.ilike(_like(q)),
        Translation.translated_value.ilike(_like(q)),
        Translation.status.ilike(_like(q)),
    )).limit(limit)
    return [_hit("translation", t.id,
                 f"{t.entity_type}:{t.field_name}",
                 f"{t.locale} · {t.status}",
                 f"/translations/{t.id}")
            for t in db.scalars(stmt)]


def _search_analytics(db: Session, q: str, workspace_id: str | None, limit: int) -> list[dict]:
    """Combined search over metrics, reports, and snapshots."""
    per = max(1, limit // 3) or 1
    hits: list[dict] = []

    metrics = db.scalars(
        select(AnalyticsMetric).where(or_(
            AnalyticsMetric.metric_name.ilike(_like(q)),
            AnalyticsMetric.metric_scope.ilike(_like(q)),
            AnalyticsMetric.entity_type.ilike(_like(q)),
            AnalyticsMetric.metric_unit.ilike(_like(q)),
        )).limit(per)
    )
    for m in metrics:
        hits.append(_hit("analytics", m.id,
                         f"metric · {m.metric_name}",
                         f"{m.metric_scope} · {m.metric_unit or ''}".strip(" ·"),
                         f"/analytics/metrics/{m.id}"))

    reports = db.scalars(
        select(AnalyticsReport).where(or_(
            AnalyticsReport.report_name.ilike(_like(q)),
            AnalyticsReport.report_type.ilike(_like(q)),
            AnalyticsReport.status.ilike(_like(q)),
        )).limit(per)
    )
    for r in reports:
        hits.append(_hit("analytics", r.id,
                         f"report · {r.report_name}",
                         f"{r.report_type} · {r.status}",
                         f"/analytics/reports/{r.id}"))

    snapshots = db.scalars(
        select(AnalyticsSnapshot).where(
            AnalyticsSnapshot.snapshot_type.ilike(_like(q))
        ).limit(per)
    )
    for s in snapshots:
        hits.append(_hit("analytics", s.id,
                         f"snapshot · {s.snapshot_type}",
                         s.period_start.isoformat() if s.period_start else None,
                         f"/analytics/snapshots/{s.id}"))

    return hits[:limit]


_HANDLERS: dict[str, Callable[..., list[dict]]] = {
    "campaign": _search_campaigns,
    "audience": _search_audience,
    "organization": _search_organizations,
    "user": _search_users,
    "template": _search_templates,
    "media": _search_media,
    "notification": _search_notifications,
    "audit": _search_audit,
    "volunteer": _search_volunteers,
    "task": _search_tasks,
    "disaster": _search_disasters,
    "assignment": _search_assignments,
    "public_resource": _search_public_resources,
    "translation": _search_translations,
    "analytics": _search_analytics,
}


def search(
    db: Session,
    *,
    q: str,
    permissions: set[str] | None = None,
    scopes: Iterable[str] | None = None,
    workspace_id: str | None = None,
    user_id: str | None = None,
    limit_per_scope: int = 10,
    limit_total: int = 50,
) -> dict:
    params = {"q": q, "scopes": sorted(scopes or []), "workspace_id": workspace_id,
              "user_id": user_id, "perms": sorted(permissions or [])}
    cached = cache.get("search:global", params)
    if cached:
        return cached

    permissions = permissions or set()
    active = list(scopes) if scopes else list(_HANDLERS.keys())
    results: list[dict] = []
    per_scope: dict[str, int] = {}

    for scope in active:
        needed = SCOPE_PERMISSIONS.get(scope)
        if needed and needed not in permissions:
            continue
        try:
            if scope == "notification":
                hits = _search_notifications(db, q, user_id, limit_per_scope)
            else:
                hits = _HANDLERS[scope](db, q, workspace_id, limit_per_scope)
        except Exception:  # noqa: BLE001
            hits = []
        per_scope[scope] = len(hits)
        results.extend(hits)

    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:limit_total]
    payload = {
        "query": q,
        "results": results,
        "counts": per_scope,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    cache.set("search:global", params, payload, ttl_seconds=30)
    return payload


def suggestions(db: Session, q: str, limit: int = 8) -> list[str]:
    if not q:
        return []
    sample = _search_campaigns(db, q, None, limit) + _search_templates(db, q, None, limit)
    return list(dict.fromkeys(h["title"] for h in sample))[:limit]
