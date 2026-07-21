"""Reporting engine: builder, scheduler-aware runner, export delivery."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analytics import Report
from app.services import analytics, export

REPORT_KINDS = {
    "executive_overview", "campaign_analytics", "audience_analytics",
    "communication_analytics", "ai_usage", "security", "notifications",
    "top_campaigns", "top_templates",
}


def _run(db: Session, kind: str, filters: dict[str, Any]) -> tuple[str, list[dict]]:
    workspace_id = filters.get("workspaceId")
    if kind == "executive_overview":
        d = analytics.executive_overview(db, workspace_id)
        return "Executive overview", d["kpis"]
    if kind == "campaign_analytics":
        d = analytics.campaign_analytics(db, workspace_id)
        return "Campaign analytics", [{"metric": k, "value": v} for k, v in _flatten(d).items()]
    if kind == "audience_analytics":
        d = analytics.audience_analytics(db, workspace_id)
        return "Audience analytics", [{"metric": k, "value": v} for k, v in _flatten(d).items()]
    if kind == "communication_analytics":
        d = analytics.communication_analytics(db, workspace_id)
        return "Communication analytics", [{"metric": k, "value": v} for k, v in _flatten(d).items()]
    if kind == "ai_usage":
        d = analytics.ai_usage_analytics(db, workspace_id)
        return "AI usage", [{"metric": k, "value": v} for k, v in _flatten(d).items()]
    if kind == "security":
        d = analytics.security_analytics(db)
        return "Security analytics", [{"metric": k, "value": v} for k, v in _flatten(d).items()]
    if kind == "notifications":
        d = analytics.notification_analytics(db)
        return "Notifications", [{"metric": k, "value": v} for k, v in _flatten(d).items()]
    if kind == "top_campaigns":
        return "Top campaigns", analytics.top_performers(db, kind="campaigns", workspace_id=workspace_id)
    if kind == "top_templates":
        return "Top templates", analytics.top_performers(db, kind="templates", workspace_id=workspace_id)
    raise ValueError(f"Unknown report kind: {kind}")


def _flatten(d: dict, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            for kk, vv in v.items():
                out[f"{key}.{kk}"] = vv
        else:
            out[key] = v
    return out


def run_report(db: Session, report: Report, *, format: str = "json") -> tuple[bytes, str, str]:
    title, rows = _run(db, report.kind, report.filters or {})
    report.last_run_at = datetime.now(timezone.utc)
    db.commit()
    return export.render(format, title=title, rows=rows)


def run_ad_hoc(db: Session, *, kind: str, filters: dict[str, Any] | None = None, format: str = "json") -> tuple[bytes, str, str]:
    if kind not in REPORT_KINDS:
        raise ValueError(f"Unknown report kind: {kind}")
    title, rows = _run(db, kind, filters or {})
    return export.render(format, title=title, rows=rows)


def create_report(db: Session, *, workspace_id: str, name: str, kind: str, scheduled: bool = False,
                  filters: dict[str, Any] | None = None) -> Report:
    if kind not in REPORT_KINDS:
        raise ValueError(f"Unknown report kind: {kind}")
    r = Report(id=uuid.uuid4(), workspace_id=workspace_id, name=name, kind=kind,
               scheduled=scheduled, filters=filters or {})
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def due_scheduled_reports(db: Session) -> list[Report]:
    stmt = select(Report).where(Report.scheduled.is_(True))
    return list(db.scalars(stmt))
