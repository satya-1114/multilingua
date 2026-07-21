"""Integration tests for Phase 6.4 — analytics notifications, audit,
search registration, and failure isolation."""
from __future__ import annotations

import types
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import analytics as an_router
from app.core.exceptions import install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.analytics import AnalyticsMetric, AnalyticsReport, AnalyticsSnapshot
from app.models.audit import AuditLog
from app.models.notification import Notification, NotificationPreference
from app.services import analytics_events
from app.services import search as search_svc


@pytest.fixture(scope="module")
def engine():
    from sqlalchemy.dialects.postgresql import JSONB
    from app.models.user import User

    for table in (
        AnalyticsMetric.__table__,
        AnalyticsSnapshot.__table__,
        AnalyticsReport.__table__,
        AuditLog.__table__,
        Notification.__table__,
        NotificationPreference.__table__,
    ):
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            column.foreign_keys = set()
        table.constraints = {
            c for c in table.constraints if type(c).__name__ != "ForeignKeyConstraint"
        }

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    for tbl in (
        User.__table__,
        AnalyticsMetric.__table__,
        AnalyticsSnapshot.__table__,
        AnalyticsReport.__table__,
        AuditLog.__table__,
        Notification.__table__,
        NotificationPreference.__table__,
    ):
        tbl.create(eng, checkfirst=True)
    return eng


@pytest.fixture
def Session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _user(role: str = "super_admin"):
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        roles=[types.SimpleNamespace(name=role)],
        is_active=True,
        deleted_at=None,
    )


def _client(Session, user):
    app = FastAPI()
    install_exception_handlers(app)
    app.include_router(an_router.router, prefix="/analytics", tags=["analytics"])

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _metric_payload(**over):
    body = {
        "metricName": "volunteers.active",
        "metricScope": "volunteer",
        "metricValue": 3.0,
        "recordedAt": _iso(datetime.now(timezone.utc)),
        "metadata": {"source": "test"},
    }
    body.update(over)
    return body


def _snapshot_payload(**over):
    now = datetime.now(timezone.utc)
    body = {
        "snapshotType": "daily",
        "periodStart": _iso(now - timedelta(days=1)),
        "periodEnd": _iso(now),
        "generatedAt": _iso(now),
        "metricsJson": {"active": 1},
        "metadata": {},
    }
    body.update(over)
    return body


def _report_payload(**over):
    body = {
        "reportName": "Weekly summary",
        "reportType": "summary",
        "metadata": {},
    }
    body.update(over)
    return body


# --------------------------------------------------------------------------- #
# Notification emission + audit logging
# --------------------------------------------------------------------------- #


def test_metric_create_emits_notification_and_audit(Session):
    user = _user()
    c = _client(Session, user)

    r = c.post("/analytics", json=_metric_payload())
    assert r.status_code == 201, r.text

    with Session() as s:
        notifs = list(s.scalars(select(Notification)))
        audits = list(s.scalars(select(AuditLog)))
    assert any(n.category == "analytics" and "metric" in n.title.lower() for n in notifs)
    assert any(a.module == "analytics_metric" and a.action == "create" for a in audits)


def test_snapshot_lifecycle_emits_events(Session):
    user = _user()
    c = _client(Session, user)
    r = c.post("/analytics/snapshots", json=_snapshot_payload(snapshotType="weekly"))
    assert r.status_code == 201, r.text
    sid = r.json()["data"]["id"]
    assert c.post(f"/analytics/snapshots/{sid}/regenerate", json={}).status_code == 200
    assert c.delete(f"/analytics/snapshots/{sid}").status_code == 200

    with Session() as s:
        actions = {a.action for a in s.scalars(select(AuditLog)) if a.module == "analytics_snapshot"}
        titles = " ".join(n.title.lower() for n in s.scalars(select(Notification)))
    assert {"create", "regenerate", "delete"}.issubset(actions)
    assert "snapshot" in titles


def test_report_full_lifecycle_emits_events(Session):
    user = _user()
    c = _client(Session, user)
    rid = c.post("/analytics/reports", json=_report_payload()).json()["data"]["id"]
    assert c.post(f"/analytics/reports/{rid}/start").status_code == 200
    assert c.post(
        f"/analytics/reports/{rid}/complete",
        json={"filePath": "/tmp/x.pdf"},
    ).status_code == 200
    future = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    assert c.post(f"/analytics/reports/{rid}/expire", json={"expiresAt": future}).status_code == 200
    assert c.delete(f"/analytics/reports/{rid}").status_code == 200

    with Session() as s:
        actions = {a.action for a in s.scalars(select(AuditLog)) if a.module == "analytics_report"}
        titles = " ".join(n.title.lower() for n in s.scalars(select(Notification)))
    assert {"request", "start_generation", "complete_generation", "expire", "delete"}.issubset(actions)
    assert "report requested" in titles and "report ready" in titles


def test_report_fail_emits_events(Session):
    user = _user()
    c = _client(Session, user)
    rid = c.post("/analytics/reports", json=_report_payload(reportName="Fails")).json()["data"]["id"]
    assert c.post(f"/analytics/reports/{rid}/start").status_code == 200
    assert c.post(f"/analytics/reports/{rid}/fail", json={"error": "boom"}).status_code == 200

    with Session() as s:
        audits = [a for a in s.scalars(select(AuditLog)) if a.module == "analytics_report"]
        notifs = list(s.scalars(select(Notification)))
    assert any(a.action == "fail_generation" and (a.metadata_ or {}).get("error") == "boom" for a in audits)
    assert any("failed" in n.title.lower() and n.priority == "high" for n in notifs)


# --------------------------------------------------------------------------- #
# Notification failure isolation
# --------------------------------------------------------------------------- #


def test_notification_failure_does_not_break_business_op(Session, monkeypatch):
    from app.services import notifications as notif_service

    def boom(*a, **kw):
        raise RuntimeError("notification down")

    user = _user()
    c = _client(Session, user)
    monkeypatch.setattr(notif_service, "create", boom)
    r = c.post("/analytics", json=_metric_payload(metricName="isolation.test"))
    assert r.status_code == 201


def test_event_helper_handles_missing_recipients(Session):
    # Passing None user_id must silently no-op — no exception raised.
    with Session() as s:
        analytics_events.metric_created(
            s,
            types.SimpleNamespace(
                id=uuid.uuid4(), metric_name="x", metric_scope="platform"
            ),
            actor_id=None,
        )


# --------------------------------------------------------------------------- #
# Search registration
# --------------------------------------------------------------------------- #


def test_search_registers_analytics_scope():
    assert "analytics" in search_svc._HANDLERS
    assert search_svc.SCOPE_PERMISSIONS.get("analytics") == "analytics:view"


def test_search_analytics_returns_hits(Session):
    user = _user()
    c = _client(Session, user)
    c.post("/analytics", json=_metric_payload(metricName="findable.metric"))
    c.post("/analytics/reports", json=_report_payload(reportName="Findable Report"))
    c.post("/analytics/snapshots", json=_snapshot_payload(snapshotType="custom"))

    with Session() as s:
        metric_hits = search_svc._search_analytics(s, "findable", None, 20)
        snap_hits = search_svc._search_analytics(s, "custom", None, 20)
    all_hits = metric_hits + snap_hits
    scopes = {h["scope"] for h in all_hits}
    titles = " ".join(h["title"] for h in all_hits).lower()
    assert scopes == {"analytics"}
    assert "metric" in titles and "report" in titles and "snapshot" in titles
