"""CSV import engine.

Provides preview, validation, duplicate detection, and job execution for
audience imports. Additional entity types can register by supplying a
transformer + repository binding.
"""
from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.audience import Audience


@dataclass
class ImportReport:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    duplicates: int = 0
    inserted: int = 0
    updated: int = 0
    errors: list[dict] = field(default_factory=list)


def _read_rows(data: bytes) -> list[dict[str, str]]:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


# ---------------------------------------------------------------- audience

AUDIENCE_HEADERS = {"email", "full_name", "phone", "language", "status", "tags"}


def _validate_audience_row(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    email = row.get("email", "")
    if not email or "@" not in email:
        errors.append("email required and must be valid")
    if row.get("language") and len(row["language"]) > 8:
        errors.append("language code too long")
    return errors


def audience_preview(data: bytes, *, sample: int = 10) -> dict:
    rows = _read_rows(data)
    report = ImportReport(total=len(rows))
    seen: set[str] = set()
    for i, row in enumerate(rows):
        errors = _validate_audience_row(row)
        if errors:
            report.invalid += 1
            report.errors.append({"row": i + 1, "errors": errors})
            continue
        email = row["email"].lower()
        if email in seen:
            report.duplicates += 1
            continue
        seen.add(email)
        report.valid += 1
    headers = list(rows[0].keys()) if rows else []
    return {
        "headers": headers,
        "sample": rows[:sample],
        "report": report.__dict__,
    }


def audience_import(
    db: Session,
    data: bytes,
    *,
    workspace_id: str,
    strategy: str = "merge",  # "merge" | "skip" | "replace"
) -> ImportReport:
    rows = _read_rows(data)
    if not rows:
        raise ValidationError("CSV contains no rows")

    report = ImportReport(total=len(rows))
    for i, row in enumerate(rows):
        errors = _validate_audience_row(row)
        if errors:
            report.invalid += 1
            report.errors.append({"row": i + 1, "errors": errors})
            continue

        email = row["email"].lower()
        payload = {
            "email": email,
            "full_name": row.get("full_name") or None,
            "phone": row.get("phone") or None,
            "language": row.get("language") or "en",
            "status": row.get("status") or "active",
            "workspace_id": workspace_id,
        }
        if row.get("tags"):
            payload["tags"] = [t.strip() for t in row["tags"].split(",") if t.strip()]

        existing = db.query(Audience).filter(
            Audience.workspace_id == workspace_id, Audience.email == email
        ).one_or_none()
        if existing:
            report.duplicates += 1
            if strategy == "skip":
                continue
            if strategy in {"merge", "replace"}:
                for k, v in payload.items():
                    if strategy == "merge" and v is None:
                        continue
                    setattr(existing, k, v)
                report.updated += 1
        else:
            db.add(Audience(id=uuid.uuid4(), **payload))
            report.inserted += 1
        report.valid += 1
    db.commit()
    return report


# ---------------------------------------------------------------- registry

IMPORTERS: dict[str, Callable[..., ImportReport]] = {
    "audience": audience_import,
}
