"""Model, schema, enum, and RBAC tests for the analytics platform.

Phase 6.1 — DB foundation only. Uses a dedicated SQLite in-memory
engine; JSONB is swapped for JSON so the tables build.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.analytics import (
    METRIC_SCOPES,
    METRIC_SCOPE_PLATFORM,
    METRIC_SCOPE_VOLUNTEER,
    REPORT_STATUSES,
    REPORT_STATUS_COMPLETED,
    REPORT_STATUS_PENDING,
    SNAPSHOT_TYPES,
    SNAPSHOT_TYPE_DAILY,
)
from app.models.analytics import AnalyticsMetric, AnalyticsReport, AnalyticsSnapshot
from app.schemas.analytics import (
    AnalyticsMetricCreate,
    AnalyticsMetricDto,
    AnalyticsReportCreate,
    AnalyticsReportDto,
    AnalyticsSnapshotCreate,
    AnalyticsSnapshotDto,
)
from app.security.rbac import has_permission


# --------------------------------------------------------------------------- #
# Test engine: JSONB -> JSON so SQLite can materialise the columns.
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def engine():
    from sqlalchemy.dialects.postgresql import JSONB

    tables = (
        AnalyticsMetric.__table__,
        AnalyticsSnapshot.__table__,
        AnalyticsReport.__table__,
    )
    for table in tables:
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
        # Strip FKs pointing at unrelated tables so we can build in isolation.
        for col in table.columns:
            col.foreign_keys = set()
        table.constraints = {
            c for c in table.constraints
            if c.__class__.__name__ != "ForeignKeyConstraint"
        }

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    for t in tables:
        t.create(eng, checkfirst=True)
    return eng


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, future=True)
    s = Session()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #


def test_enum_membership():
    assert METRIC_SCOPE_PLATFORM in METRIC_SCOPES
    assert METRIC_SCOPE_VOLUNTEER in METRIC_SCOPES
    assert REPORT_STATUS_PENDING in REPORT_STATUSES
    assert REPORT_STATUS_COMPLETED in REPORT_STATUSES
    assert SNAPSHOT_TYPE_DAILY in SNAPSHOT_TYPES
    assert len(METRIC_SCOPES) == 6
    assert len(REPORT_STATUSES) == 4
    assert len(SNAPSHOT_TYPES) == 4


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #


def test_metric_create_defaults():
    dto = AnalyticsMetricCreate(
        metric_name="volunteer.count",
        metric_scope="volunteer",
        recorded_at=datetime.now(timezone.utc),
    )
    assert dto.metricValue == 0.0
    assert dto.metadata == {}
    assert dto.entityId is None


def test_metric_create_rejects_bad_scope():
    with pytest.raises(ValidationError):
        AnalyticsMetricCreate(
            metric_name="x",
            metric_scope="nonsense",
            recorded_at=datetime.now(timezone.utc),
        )


def test_snapshot_create_rejects_inverted_period():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        AnalyticsSnapshotCreate(
            snapshot_type="daily",
            period_start=now,
            period_end=now - timedelta(days=1),
            generated_at=now,
        )


def test_snapshot_create_ok():
    now = datetime.now(timezone.utc)
    dto = AnalyticsSnapshotCreate(
        snapshot_type="daily",
        period_start=now - timedelta(days=1),
        period_end=now,
        generated_at=now,
        metrics_json={"reach": 100},
    )
    assert dto.metricsJson == {"reach": 100}


def test_report_create_defaults():
    dto = AnalyticsReportCreate(
        report_name="Weekly Volunteer",
        report_type="volunteer_weekly",
    )
    assert dto.status == "pending"
    assert dto.metadata == {}


def test_report_create_rejects_bad_status():
    with pytest.raises(ValidationError):
        AnalyticsReportCreate(
            report_name="X", report_type="y", status="unknown"
        )


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


def test_metric_persists_polymorphic_entity(session):
    m = AnalyticsMetric(
        metric_name="disaster.opened",
        metric_scope="disaster",
        entity_type="disaster",
        entity_id=uuid.uuid4(),
        metric_value=1,
        metric_unit="count",
        recorded_at=datetime.now(timezone.utc),
        metadata_={"source": "unit"},
    )
    session.add(m)
    session.commit()
    fetched = session.get(AnalyticsMetric, m.id)
    assert fetched is not None
    assert fetched.metric_scope == "disaster"
    assert fetched.metadata_ == {"source": "unit"}


def test_snapshot_persists(session):
    now = datetime.now(timezone.utc)
    snap = AnalyticsSnapshot(
        snapshot_type="daily",
        period_start=now - timedelta(days=1),
        period_end=now,
        generated_at=now,
        metrics_json={"kpi": 42},
        metadata_={},
    )
    session.add(snap)
    session.commit()
    assert session.get(AnalyticsSnapshot, snap.id).metrics_json == {"kpi": 42}


def test_report_persists(session):
    rep = AnalyticsReport(
        report_name="Monthly Ops",
        report_type="ops_monthly",
        status="pending",
    )
    session.add(rep)
    session.commit()
    fetched = session.get(AnalyticsReport, rep.id)
    assert fetched.report_name == "Monthly Ops"
    assert fetched.status == "pending"


def test_metric_dto_from_dict():
    now = datetime.now(timezone.utc)
    dto = AnalyticsMetricDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "metric_name": "platform.uptime",
            "metric_scope": "platform",
            "metric_value": 99.9,
            "recorded_at": now,
            "metadata": {"host": "web1"},
        }
    )
    assert dto.metricScope == "platform"
    assert dto.metadata == {"host": "web1"}


def test_snapshot_dto_from_dict():
    now = datetime.now(timezone.utc)
    dto = AnalyticsSnapshotDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "snapshot_type": "weekly",
            "period_start": now - timedelta(days=7),
            "period_end": now,
            "generated_at": now,
            "metrics_json": {"a": 1},
            "metadata": {},
        }
    )
    assert dto.snapshotType == "weekly"
    assert dto.metricsJson == {"a": 1}


def test_report_dto_from_dict():
    now = datetime.now(timezone.utc)
    dto = AnalyticsReportDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "report_name": "Weekly",
            "report_type": "vw",
            "status": "completed",
            "metadata": {"rows": 10},
        }
    )
    assert dto.status == "completed"
    assert dto.metadata == {"rows": 10}


# --------------------------------------------------------------------------- #
# Indexes
# --------------------------------------------------------------------------- #


def test_expected_indexes_defined():
    metric_idx = {i.name for i in AnalyticsMetric.__table__.indexes}
    assert {
        "ix_analytics_metrics_scope",
        "ix_analytics_metrics_entity",
        "ix_analytics_metrics_name",
        "ix_analytics_metrics_recorded_at",
    }.issubset(metric_idx)

    snap_idx = {i.name for i in AnalyticsSnapshot.__table__.indexes}
    assert {
        "ix_analytics_snapshots_type",
        "ix_analytics_snapshots_period",
    }.issubset(snap_idx)

    rep_idx = {i.name for i in AnalyticsReport.__table__.indexes}
    assert {
        "ix_analytics_reports_status",
        "ix_analytics_reports_generated_at",
    }.issubset(rep_idx)


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #


def test_rbac_grants():
    assert has_permission(["super_admin"], "analytics:manage")
    assert has_permission(["org_admin"], "analytics:manage")
    assert has_permission(["org_admin"], "analytics:export")
    assert has_permission(["data_analyst"], "analytics:view")
    assert has_permission(["data_analyst"], "analytics:export")
    assert has_permission(["data_analyst"], "analytics:manage")
    assert has_permission(["viewer"], "analytics:view")
    assert not has_permission(["viewer"], "analytics:export")
    assert not has_permission(["viewer"], "analytics:manage")
    assert not has_permission(["volunteer"], "analytics:view")
