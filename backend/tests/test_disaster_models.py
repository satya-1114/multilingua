"""Schema & enum tests for the Disaster module (Phase 3.1 — DB foundation).

No repository/service/router yet; these tests validate that models import
cleanly, that Pydantic schemas coerce the ORM shape, and that the
constants module stays the single source of truth for enum literals.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.constants.disaster import (
    ASSIGNMENT_STATUSES,
    ASSIGNMENT_STATUS_ASSIGNED,
    ASSIGNMENT_STATUS_COMPLETED,
    ATTACHMENT_KINDS,
    DISASTER_SEVERITIES,
    DISASTER_STATUSES,
    DISASTER_STATUSES_OPEN,
    DISASTER_STATUSES_TERMINAL,
    DISASTER_STATUS_REPORTED,
    DISASTER_STATUS_RESOLVED,
    DISASTER_TYPES,
    DISASTER_TYPE_FLOOD,
)
from app.models.disaster import Disaster, DisasterAssignment, DisasterAttachment
from app.schemas.disaster import (
    DisasterAssignmentCreate,
    DisasterAssignmentDto,
    DisasterAttachmentCreate,
    DisasterCreate,
    DisasterDto,
    DisasterStatusUpdate,
    DisasterUpdate,
)
from app.security.rbac import has_permission


def test_enum_membership_matches_schema_literals():
    assert DISASTER_TYPE_FLOOD in DISASTER_TYPES
    assert DISASTER_STATUS_REPORTED in DISASTER_STATUSES
    assert ASSIGNMENT_STATUS_ASSIGNED in ASSIGNMENT_STATUSES
    assert "critical" in DISASTER_SEVERITIES
    assert "image" in ATTACHMENT_KINDS


def test_open_and_terminal_status_partitions_are_disjoint():
    assert set(DISASTER_STATUSES_OPEN).isdisjoint(DISASTER_STATUSES_TERMINAL)
    assert set(DISASTER_STATUSES_OPEN) | set(DISASTER_STATUSES_TERMINAL) == set(
        DISASTER_STATUSES
    )
    assert DISASTER_STATUS_RESOLVED in DISASTER_STATUSES_TERMINAL


def test_disaster_create_validates_and_defaults():
    payload = DisasterCreate(title="Chennai floods", disasterType="flood")
    assert payload.severity == "medium"
    assert payload.status == "reported"
    assert payload.metadata == {}


def test_disaster_create_rejects_invalid_type():
    with pytest.raises(Exception):
        DisasterCreate(title="x", disasterType="volcano")  # type: ignore[arg-type]


def test_disaster_create_rejects_out_of_range_geo():
    with pytest.raises(Exception):
        DisasterCreate(title="x", disasterType="flood", latitude=95.0)
    with pytest.raises(Exception):
        DisasterCreate(title="x", disasterType="flood", longitude=-200.0)


def test_disaster_status_update_accepts_optional_resolved_at():
    now = datetime.now(timezone.utc)
    upd = DisasterStatusUpdate(status="resolved", resolvedAt=now)
    assert upd.status == "resolved"
    assert upd.resolvedAt == now


def test_disaster_update_is_all_optional():
    upd = DisasterUpdate()
    dumped = upd.model_dump(exclude_none=True)
    assert dumped == {}


def test_disaster_assignment_create_defaults():
    a = DisasterAssignmentCreate(volunteerId=uuid.uuid4())
    assert a.role is None
    assert a.notes is None


def test_disaster_attachment_create_defaults_to_image():
    att = DisasterAttachmentCreate(fileName="photo.jpg", fileUrl="https://x/y.jpg")
    assert att.kind == "image"


def test_dto_serialization_from_snake_case_dict():
    now = datetime.now(timezone.utc)
    dto = DisasterDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "title": "Fire in warehouse",
            "disaster_type": "fire",
            "severity": "high",
            "status": "active",
            "latitude": 13.0,
            "longitude": 80.2,
            "city": "Chennai",
            "state": "TN",
            "country": "IN",
            "started_at": now,
            "metadata_": {"source": "sms"},
        }
    )
    assert dto.title == "Fire in warehouse"
    assert dto.disasterType == "fire"
    assert dto.metadata == {"source": "sms"}
    assert dto.startedAt == now


def test_assignment_dto_maps_snake_case():
    now = datetime.now(timezone.utc)
    dto = DisasterAssignmentDto.model_validate(
        {
            "id": uuid.uuid4(),
            "createdAt": now,
            "updatedAt": now,
            "disaster_id": uuid.uuid4(),
            "volunteer_id": uuid.uuid4(),
            "role": "medic",
            "status": ASSIGNMENT_STATUS_COMPLETED,
            "assigned_at": now,
            "completed_at": now,
        }
    )
    assert dto.role == "medic"
    assert dto.status == "completed"


def test_models_are_registered_on_metadata():
    from app.database.base import Base

    tables = set(Base.metadata.tables)
    assert "disasters" in tables
    assert "disaster_assignments" in tables
    assert "disaster_attachments" in tables


def test_model_indexes_and_constraints():
    assert "uq_disaster_assignment_volunteer" in {
        c.name for c in DisasterAssignment.__table__.constraints
    }
    idx = {i.name for i in Disaster.__table__.indexes}
    assert "ix_disasters_org_status" in idx
    assert "ix_disasters_type_status" in idx
    assert "ix_disasters_severity_status" in idx
    assert "ix_disaster_attachments_disaster_kind" in {
        i.name for i in DisasterAttachment.__table__.indexes
    }


def test_rbac_grants_new_disaster_permissions():
    # org_admin gets disaster:* and assignment:*
    assert has_permission(["org_admin"], "disaster:create")
    assert has_permission(["org_admin"], "assignment:manage")

    # campaign_manager gets explicit non-wildcard grants
    assert has_permission(["campaign_manager"], "disaster:view")
    assert has_permission(["campaign_manager"], "disaster:manage")
    assert has_permission(["campaign_manager"], "assignment:manage")

    # volunteer can act on their own assignments and view disasters
    assert has_permission(["volunteer"], "disaster:view")
    assert has_permission(["volunteer"], "assignment:act")
    assert not has_permission(["volunteer"], "disaster:create")

    # viewer is read-only
    assert has_permission(["viewer"], "disaster:view")
    assert not has_permission(["viewer"], "disaster:update")
