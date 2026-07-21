"""Router-level tests for the Analytics Platform (Phase 6.3).

Uses an isolated in-memory SQLite engine with JSONB swapped for JSON and
cross-table FKs stripped — same pattern as ``test_analytics``.
"""
from __future__ import annotations

import types
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import analytics as an_router
from app.core.exceptions import install_exception_handlers
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.analytics import AnalyticsMetric, AnalyticsReport, AnalyticsSnapshot
from app.models.audit import AuditLog
from app.models.notification import Notification, NotificationPreference


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def engine():
    from sqlalchemy.dialects.postgresql import JSONB

    tables = (
        AnalyticsMetric.__table__,
        AnalyticsSnapshot.__table__,
        AnalyticsReport.__table__,
        AuditLog.__table__,
        Notification.__table__,
        NotificationPreference.__table__,
    )
    for table in tables:
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
    for table in tables:
        table.create(eng, checkfirst=True)
    return eng


@pytest.fixture
def Session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _user(role: str):
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


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


def _metric_payload(**over):
    body = {
        "metricName": "volunteers.active",
        "metricScope": "volunteer",
        "metricValue": 5.0,
        "recordedAt": _iso(datetime.now(timezone.utc)),
        "metadata": {"source": "test"},
    }
    body.update(over)
    return body


def test_metric_crud_and_envelope(Session):
    c = _client(Session, _user("super_admin"))

    r = c.post("/analytics", json=_metric_payload())
    assert r.status_code == 201, r.text
    env = r.json()
    assert env["success"] is True
    assert env["meta"]["requestId"].startswith("req_")
    mid = env["data"]["id"]
    assert env["data"]["metricName"] == "volunteers.active"

    g = c.get(f"/analytics/{mid}")
    assert g.status_code == 200
    assert g.json()["data"]["metricValue"] == 5.0

    u = c.patch(f"/analytics/{mid}", json={"metricValue": 12.5, "metricUnit": "count"})
    assert u.status_code == 200
    assert u.json()["data"]["metricValue"] == 12.5
    assert u.json()["data"]["metricUnit"] == "count"

    d = c.delete(f"/analytics/{mid}")
    assert d.status_code == 200
    assert d.json()["data"]["deleted"] is True


def test_metric_list_pagination(Session):
    c = _client(Session, _user("super_admin"))
    for i in range(3):
        r = c.post(
            "/analytics",
            json=_metric_payload(
                metricName=f"scan.count.{i}", metricValue=float(i)
            ),
        )
        assert r.status_code == 201

    lst = c.get("/analytics", params={"page": 1, "pageSize": 2})
    assert lst.status_code == 200
    body = lst.json()
    assert body["pagination"]["pageSize"] == 2
    assert body["pagination"]["total"] >= 3
    assert len(body["data"]) == 2


def test_metric_aggregate(Session):
    c = _client(Session, _user("super_admin"))
    name = f"agg.{uuid.uuid4().hex[:6]}"
    for v in (2.0, 4.0, 6.0):
        c.post("/analytics", json=_metric_payload(metricName=name, metricValue=v))

    r = c.get("/analytics/aggregate", params={"metricName": name})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["count"] == 3
    assert data["sum"] == 12.0
    assert data["avg"] == 4.0
    assert data["min"] == 2.0
    assert data["max"] == 6.0


def test_metric_rbac_denied_for_viewer(Session):
    c = _client(Session, _user("viewer"))
    r = c.post("/analytics", json=_metric_payload())
    assert r.status_code == 403


def test_metric_rbac_viewer_can_list(Session):
    _client(Session, _user("super_admin")).post("/analytics", json=_metric_payload())
    r = _client(Session, _user("viewer")).get("/analytics")
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# Snapshots
# --------------------------------------------------------------------------- #


def _snapshot_payload(**over):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    body = {
        "snapshotType": "daily",
        "periodStart": _iso(start),
        "periodEnd": _iso(start + timedelta(days=1)),
        "generatedAt": _iso(start),
        "metricsJson": {"active": 10},
    }
    body.update(over)
    return body


def test_snapshot_crud_and_latest(Session):
    c = _client(Session, _user("super_admin"))

    r = c.post("/analytics/snapshots", json=_snapshot_payload())
    assert r.status_code == 201, r.text
    sid = r.json()["data"]["id"]

    g = c.get(f"/analytics/snapshots/{sid}")
    assert g.status_code == 200
    assert g.json()["data"]["metricsJson"] == {"active": 10}

    lst = c.get("/analytics/snapshots", params={"snapshotType": "daily"})
    assert lst.status_code == 200
    assert lst.json()["pagination"]["total"] >= 1

    latest = c.get("/analytics/snapshots/latest", params={"snapshotType": "daily"})
    assert latest.status_code == 200
    assert latest.json()["data"]["id"] == sid

    regen = c.post(
        f"/analytics/snapshots/{sid}/regenerate",
        json={"metricsJson": {"active": 20}},
    )
    assert regen.status_code == 200
    assert regen.json()["data"]["metricsJson"] == {"active": 20}

    d = c.delete(f"/analytics/snapshots/{sid}")
    assert d.status_code == 200


def test_snapshot_duplicate_period_conflict(Session):
    c = _client(Session, _user("super_admin"))
    start = datetime(2026, 2, 1, tzinfo=timezone.utc)
    payload = _snapshot_payload(
        periodStart=_iso(start), periodEnd=_iso(start + timedelta(days=1))
    )
    r1 = c.post("/analytics/snapshots", json=payload)
    assert r1.status_code == 201
    r2 = c.post("/analytics/snapshots", json=payload)
    assert r2.status_code == 409


def test_snapshot_rbac(Session):
    c = _client(Session, _user("viewer"))
    r = c.post("/analytics/snapshots", json=_snapshot_payload())
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #


def _report_payload(**over):
    body = {"reportName": "Weekly Ops", "reportType": "operational"}
    body.update(over)
    return body


def test_report_lifecycle(Session):
    c = _client(Session, _user("super_admin"))

    r = c.post("/analytics/reports", json=_report_payload())
    assert r.status_code == 201, r.text
    rid = r.json()["data"]["id"]
    assert r.json()["data"]["status"] == "pending"

    started = c.post(f"/analytics/reports/{rid}/start")
    assert started.status_code == 200
    assert started.json()["data"]["status"] == "generating"

    completed = c.post(
        f"/analytics/reports/{rid}/complete",
        json={"filePath": "/tmp/report.pdf"},
    )
    assert completed.status_code == 200
    assert completed.json()["data"]["status"] == "completed"
    assert completed.json()["data"]["filePath"] == "/tmp/report.pdf"

    expired = c.post(f"/analytics/reports/{rid}/expire", json={})
    assert expired.status_code == 200
    assert expired.json()["data"]["expiresAt"] is not None

    d = c.delete(f"/analytics/reports/{rid}")
    assert d.status_code == 200


def test_report_invalid_transition(Session):
    c = _client(Session, _user("super_admin"))
    rid = c.post("/analytics/reports", json=_report_payload()).json()["data"]["id"]
    # pending -> complete (skip generating) is invalid
    r = c.post(
        f"/analytics/reports/{rid}/complete", json={"filePath": "/tmp/x.pdf"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["details"]["from"] == "pending"


def test_report_fail_flow(Session):
    c = _client(Session, _user("super_admin"))
    rid = c.post("/analytics/reports", json=_report_payload()).json()["data"]["id"]
    c.post(f"/analytics/reports/{rid}/start")
    failed = c.post(
        f"/analytics/reports/{rid}/fail", json={"error": "boom"}
    )
    assert failed.status_code == 200
    assert failed.json()["data"]["status"] == "failed"
    assert failed.json()["data"]["metadata"]["error"] == "boom"


def test_report_list_and_filter(Session):
    c = _client(Session, _user("super_admin"))
    c.post("/analytics/reports", json=_report_payload(reportName="A"))
    c.post("/analytics/reports", json=_report_payload(reportName="B"))
    lst = c.get("/analytics/reports", params={"status": "pending", "pageSize": 50})
    assert lst.status_code == 200
    body = lst.json()
    assert body["pagination"]["total"] >= 2
    assert all(r["status"] == "pending" for r in body["data"])


def test_report_rbac_export_required(Session):
    # viewer has analytics:view but not analytics:export
    c = _client(Session, _user("viewer"))
    r = c.post("/analytics/reports", json=_report_payload())
    assert r.status_code == 403
