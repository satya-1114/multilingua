"""Analytics service tests.

Covers the legacy helper functions (Phase 6.0) plus the new Analytics
Platform repositories and services introduced in Phase 6.2.

Uses a dedicated in-memory SQLite engine with JSONB swapped for JSON and
FKs stripped so the analytics tables build in isolation — same pattern
as ``test_analytics_models``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

from app.constants.analytics import (
    METRIC_SCOPE_PLATFORM,
    METRIC_SCOPE_VOLUNTEER,
    REPORT_STATUS_COMPLETED,
    REPORT_STATUS_FAILED,
    REPORT_STATUS_GENERATING,
    REPORT_STATUS_PENDING,
    SNAPSHOT_TYPE_DAILY,
    SNAPSHOT_TYPE_WEEKLY,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.analytics import AnalyticsMetric, AnalyticsReport, AnalyticsSnapshot
from app.repositories.analytics import (
    AnalyticsMetricRepository,
    AnalyticsReportRepository,
    AnalyticsSnapshotRepository,
)
from app.security.rbac import has_permission
from app.services.analytics import (
    REPORT_TRANSITIONS,
    AnalyticsMetricService,
    AnalyticsReportService,
    AnalyticsSnapshotService,
    _growth,
    _moving_average,
    _percentiles,
    _range,
)


# --------------------------------------------------------------------------- #
# Legacy helpers (Phase 6.0) — preserved behaviour.
# --------------------------------------------------------------------------- #


def test_growth_and_moving_average():
    assert _growth(0, 0) == 0.0
    assert _growth(100, 0) == 100.0
    assert _growth(150, 100) == 50.0
    assert _moving_average([1, 2, 3, 4, 5], window=3) == [1.0, 1.5, 2.0, 3.0, 4.0]
    p = _percentiles([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert p["p50"] > 0 and p["p95"] >= p["p50"]


def test_range_defaults():
    start, end = _range(None, None, days=7)
    assert end - start == timedelta(days=7)
    assert end.tzinfo is timezone.utc


# --------------------------------------------------------------------------- #
# Isolated SQLite engine — swap JSONB for JSON, strip cross-table FKs.
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
        for col in table.columns:
            col.foreign_keys = set()
        table.constraints = {
            c
            for c in table.constraints
            if type(c).__name__ != "ForeignKeyConstraint"
        }

    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, future=True
    )
    for table in tables:
        table.create(eng)
    return eng


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        for table in (
            AnalyticsMetric.__table__,
            AnalyticsSnapshot.__table__,
            AnalyticsReport.__table__,
        ):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture
def metric_service():
    return AnalyticsMetricService(repo=AnalyticsMetricRepository())


@pytest.fixture
def snapshot_service():
    return AnalyticsSnapshotService(repo=AnalyticsSnapshotRepository())


@pytest.fixture
def report_service():
    return AnalyticsReportService(repo=AnalyticsReportRepository())


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #


def test_rbac_permissions_grant_matrix():
    assert has_permission(["super_admin"], "analytics:view")
    assert has_permission(["org_admin"], "analytics:manage")
    assert has_permission(["data_analyst"], "analytics:export")
    assert has_permission(["viewer"], "analytics:view")
    assert not has_permission(["viewer"], "analytics:manage")
    assert not has_permission(["translator"], "analytics:view")


# --------------------------------------------------------------------------- #
# AnalyticsMetricService
# --------------------------------------------------------------------------- #


class TestMetricService:
    def test_record_and_get(self, db, metric_service):
        m = metric_service.record_metric(
            db,
            metric_name="volunteers.active",
            metric_scope=METRIC_SCOPE_VOLUNTEER,
            metric_value=42,
        )
        assert m.id is not None
        fetched = metric_service.get_metric(db, m.id)
        assert fetched.metric_value == 42

    def test_invalid_scope_rejected(self, db, metric_service):
        with pytest.raises(ValidationError):
            metric_service.record_metric(
                db, metric_name="x", metric_scope="not_a_scope", metric_value=1
            )

    def test_entity_ref_must_be_paired(self, db, metric_service):
        with pytest.raises(ValidationError):
            metric_service.record_metric(
                db,
                metric_name="x",
                metric_scope=METRIC_SCOPE_PLATFORM,
                entity_type="volunteer",
                entity_id=None,
            )
        with pytest.raises(ValidationError):
            metric_service.record_metric(
                db,
                metric_name="x",
                metric_scope=METRIC_SCOPE_PLATFORM,
                entity_type=None,
                entity_id=uuid.uuid4(),
            )

    def test_update_ignores_immutable_entity_ref(self, db, metric_service):
        m = metric_service.record_metric(
            db,
            metric_name="x",
            metric_scope=METRIC_SCOPE_PLATFORM,
            metric_value=1,
            entity_type="volunteer",
            entity_id=uuid.uuid4(),
        )
        original_type = m.entity_type
        updated = metric_service.update_metric(db, m.id, metric_value=99)
        assert updated.metric_value == 99
        assert updated.entity_type == original_type

    def test_delete_metric_soft_deletes(self, db, metric_service):
        m = metric_service.record_metric(
            db, metric_name="x", metric_scope=METRIC_SCOPE_PLATFORM
        )
        metric_service.delete_metric(db, m.id)
        with pytest.raises(NotFoundError):
            metric_service.get_metric(db, m.id)

    def test_search_pagination_and_scope_filter(self, db, metric_service):
        for i in range(5):
            metric_service.record_metric(
                db,
                metric_name=f"vol.metric.{i}",
                metric_scope=METRIC_SCOPE_VOLUNTEER,
                metric_value=i,
            )
        metric_service.record_metric(
            db,
            metric_name="platform.metric",
            metric_scope=METRIC_SCOPE_PLATFORM,
        )
        items, total = metric_service.search_metrics(
            db, metric_scope=METRIC_SCOPE_VOLUNTEER, page=1, page_size=3
        )
        assert total == 5
        assert len(items) == 3

    def test_search_query_matches_metric_name(self, db, metric_service):
        metric_service.record_metric(
            db, metric_name="alpha.count", metric_scope=METRIC_SCOPE_PLATFORM
        )
        metric_service.record_metric(
            db, metric_name="beta.count", metric_scope=METRIC_SCOPE_PLATFORM
        )
        items, total = metric_service.search_metrics(db, query="alpha")
        assert total == 1
        assert items[0].metric_name == "alpha.count"

    def test_search_rejects_invalid_scope(self, db, metric_service):
        with pytest.raises(ValidationError):
            metric_service.search_metrics(db, metric_scope="nope")

    def test_aggregate_sum_avg_min_max(self, db, metric_service):
        for value in (10, 20, 30, 40):
            metric_service.record_metric(
                db,
                metric_name="tickets",
                metric_scope=METRIC_SCOPE_PLATFORM,
                metric_value=value,
            )
        agg = metric_service.aggregate(
            db, metric_name="tickets", metric_scope=METRIC_SCOPE_PLATFORM
        )
        assert agg["count"] == 4
        assert agg["sum"] == 100
        assert agg["avg"] == 25
        assert agg["min"] == 10
        assert agg["max"] == 40

    def test_aggregate_rejects_bad_range(self, db, metric_service):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            metric_service.aggregate(
                db,
                metric_name="x",
                recorded_from=now,
                recorded_to=now - timedelta(days=1),
            )


# --------------------------------------------------------------------------- #
# AnalyticsSnapshotService
# --------------------------------------------------------------------------- #


class TestSnapshotService:
    def _period(self, days: int = 1):
        end = datetime.now(timezone.utc)
        return end - timedelta(days=days), end

    def test_generate_snapshot(self, db, snapshot_service):
        start, end = self._period()
        snap = snapshot_service.generate_snapshot(
            db,
            snapshot_type=SNAPSHOT_TYPE_DAILY,
            period_start=start,
            period_end=end,
            metrics_json={"active_volunteers": 5},
        )
        assert snap.id is not None
        assert snap.metrics_json == {"active_volunteers": 5}

    def test_invalid_period_rejected(self, db, snapshot_service):
        end = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            snapshot_service.generate_snapshot(
                db,
                snapshot_type=SNAPSHOT_TYPE_DAILY,
                period_start=end,
                period_end=end - timedelta(hours=1),
            )

    def test_invalid_snapshot_type_rejected(self, db, snapshot_service):
        start, end = self._period()
        with pytest.raises(ValidationError):
            snapshot_service.generate_snapshot(
                db,
                snapshot_type="hourly",
                period_start=start,
                period_end=end,
            )

    def test_duplicate_period_conflicts(self, db, snapshot_service):
        start, end = self._period()
        snapshot_service.generate_snapshot(
            db, snapshot_type=SNAPSHOT_TYPE_DAILY, period_start=start, period_end=end
        )
        with pytest.raises(ConflictError):
            snapshot_service.generate_snapshot(
                db,
                snapshot_type=SNAPSHOT_TYPE_DAILY,
                period_start=start,
                period_end=end,
            )

    def test_regenerate_updates_metrics_and_generated_at(self, db, snapshot_service):
        start, end = self._period()
        snap = snapshot_service.generate_snapshot(
            db, snapshot_type=SNAPSHOT_TYPE_DAILY, period_start=start, period_end=end
        )
        prev_generated = snap.generated_at
        updated = snapshot_service.regenerate_snapshot(
            db, snap.id, metrics_json={"x": 1}
        )
        assert updated.metrics_json == {"x": 1}
        assert updated.generated_at >= prev_generated

    def test_latest_snapshot(self, db, snapshot_service):
        base = datetime.now(timezone.utc)
        for i in range(3):
            snapshot_service.generate_snapshot(
                db,
                snapshot_type=SNAPSHOT_TYPE_DAILY,
                period_start=base - timedelta(days=i + 1),
                period_end=base - timedelta(days=i),
            )
        latest = snapshot_service.latest_snapshot(
            db, snapshot_type=SNAPSHOT_TYPE_DAILY
        )
        assert latest is not None
        # Latest is the snapshot with the largest period_start (compare naive
        # because SQLite drops tzinfo on round-trip).
        expected = (base - timedelta(days=1)).replace(tzinfo=None)
        actual = latest.period_start.replace(tzinfo=None)
        assert actual == expected

    def test_get_missing_snapshot_raises(self, db, snapshot_service):
        with pytest.raises(NotFoundError):
            snapshot_service.get_snapshot(db, uuid.uuid4())

    def test_delete_snapshot(self, db, snapshot_service):
        start, end = self._period()
        snap = snapshot_service.generate_snapshot(
            db, snapshot_type=SNAPSHOT_TYPE_WEEKLY, period_start=start, period_end=end
        )
        snapshot_service.delete_snapshot(db, snap.id)
        with pytest.raises(NotFoundError):
            snapshot_service.get_snapshot(db, snap.id)


# --------------------------------------------------------------------------- #
# AnalyticsReportService — workflow transitions.
# --------------------------------------------------------------------------- #


class TestReportService:
    def _request(self, db, report_service):
        return report_service.request_report(
            db, report_name="Weekly Ops", report_type="ops"
        )

    def test_request_creates_pending(self, db, report_service):
        rep = self._request(db, report_service)
        assert rep.status == REPORT_STATUS_PENDING
        assert rep.generated_at is None

    def test_request_requires_name_and_type(self, db, report_service):
        with pytest.raises(ValidationError):
            report_service.request_report(db, report_name="", report_type="ops")
        with pytest.raises(ValidationError):
            report_service.request_report(db, report_name="ok", report_type="")

    def test_lifecycle_pending_generating_completed(self, db, report_service):
        rep = self._request(db, report_service)
        rep = report_service.start_generation(db, rep.id)
        assert rep.status == REPORT_STATUS_GENERATING
        future = datetime.now(timezone.utc) + timedelta(days=1)
        rep = report_service.complete_generation(
            db, rep.id, file_path="/tmp/report.pdf", expires_at=future
        )
        assert rep.status == REPORT_STATUS_COMPLETED
        assert rep.file_path == "/tmp/report.pdf"
        assert rep.generated_at is not None
        assert rep.expires_at.replace(tzinfo=None) == future.replace(tzinfo=None)

    def test_complete_requires_file_path(self, db, report_service):
        rep = self._request(db, report_service)
        report_service.start_generation(db, rep.id)
        with pytest.raises(ValidationError):
            report_service.complete_generation(db, rep.id, file_path="")

    def test_complete_rejects_past_expiry(self, db, report_service):
        rep = self._request(db, report_service)
        report_service.start_generation(db, rep.id)
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(ValidationError):
            report_service.complete_generation(
                db, rep.id, file_path="/tmp/x", expires_at=past
            )

    def test_fail_from_generating(self, db, report_service):
        rep = self._request(db, report_service)
        report_service.start_generation(db, rep.id)
        rep = report_service.fail_generation(db, rep.id, error="boom")
        assert rep.status == REPORT_STATUS_FAILED
        assert rep.metadata_.get("error") == "boom"

    def test_illegal_transition_rejected(self, db, report_service):
        rep = self._request(db, report_service)
        # pending -> completed (skipping generating) must fail.
        with pytest.raises(ValidationError):
            report_service.complete_generation(db, rep.id, file_path="/tmp/x")

    def test_completed_is_terminal(self, db, report_service):
        rep = self._request(db, report_service)
        report_service.start_generation(db, rep.id)
        report_service.complete_generation(db, rep.id, file_path="/tmp/x")
        with pytest.raises(ValidationError):
            report_service.fail_generation(db, rep.id)
        with pytest.raises(ValidationError):
            report_service.start_generation(db, rep.id)

    def test_expire_requires_completed(self, db, report_service):
        rep = self._request(db, report_service)
        with pytest.raises(ValidationError):
            report_service.expire_report(db, rep.id)

    def test_expire_completed_report(self, db, report_service):
        rep = self._request(db, report_service)
        report_service.start_generation(db, rep.id)
        report_service.complete_generation(db, rep.id, file_path="/tmp/x")
        rep = report_service.expire_report(db, rep.id)
        assert rep.expires_at is not None

    def test_list_reports_filter_and_paginate(self, db, report_service):
        for i in range(4):
            report_service.request_report(
                db, report_name=f"R{i}", report_type="ops"
            )
        report_service.request_report(
            db, report_name="Other", report_type="finance"
        )
        items, total = report_service.list_reports(
            db, report_type="ops", page=1, page_size=2
        )
        assert total == 4
        assert len(items) == 2

    def test_list_rejects_invalid_status(self, db, report_service):
        with pytest.raises(ValidationError):
            report_service.list_reports(db, status="archived")

    def test_delete_report(self, db, report_service):
        rep = self._request(db, report_service)
        report_service.delete_report(db, rep.id)
        with pytest.raises(NotFoundError):
            report_service.get_report(db, rep.id)


def test_report_transition_map_is_deterministic():
    # pending -> {generating, failed}; generating -> {completed, failed}; terminal states have none.
    assert REPORT_TRANSITIONS[REPORT_STATUS_PENDING] == frozenset(
        {REPORT_STATUS_GENERATING, REPORT_STATUS_FAILED}
    )
    assert REPORT_TRANSITIONS[REPORT_STATUS_GENERATING] == frozenset(
        {REPORT_STATUS_COMPLETED, REPORT_STATUS_FAILED}
    )
    assert REPORT_TRANSITIONS[REPORT_STATUS_COMPLETED] == frozenset()
    assert REPORT_TRANSITIONS[REPORT_STATUS_FAILED] == frozenset()
