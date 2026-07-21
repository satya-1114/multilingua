"""Cron expression utilities (Phase 8.3).

Thin wrapper around :class:`celery.schedules.crontab` for validation
and next-run computation. Standard 5-field cron format is supported:

    minute hour day-of-month month day-of-week
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Final

from celery.schedules import crontab
from celery.schedules import ParseException as _CeleryParseException


class CronValidationError(ValueError):
    """Raised when a cron expression is malformed."""


_ALIASES: Final[dict[str, str]] = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}


def _normalize(expr: str) -> str:
    if not isinstance(expr, str):
        raise CronValidationError("cron expression must be a string")
    stripped = expr.strip()
    if not stripped:
        raise CronValidationError("cron expression must not be empty")
    return _ALIASES.get(stripped.lower(), stripped)


def parse_cron(expr: str) -> crontab:
    normalized = _normalize(expr)
    parts = normalized.split()
    if len(parts) != 5:
        raise CronValidationError(
            f"cron expression must have 5 fields, got {len(parts)}: {expr!r}"
        )
    minute, hour, day_of_month, month_of_year, day_of_week = parts
    try:
        return crontab(
            minute=minute,
            hour=hour,
            day_of_month=day_of_month,
            month_of_year=month_of_year,
            day_of_week=day_of_week,
        )
    except (_CeleryParseException, ValueError, KeyError) as exc:
        raise CronValidationError(f"invalid cron expression {expr!r}: {exc}") from exc


def validate_cron(expr: str) -> bool:
    try:
        parse_cron(expr)
    except CronValidationError:
        return False
    return True


def next_run_at(expr: str, *, now: datetime | None = None) -> datetime:
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    # Rebuild crontab bound to the provided reference so
    # remaining_estimate uses the requested wall clock.
    normalized = _normalize(expr)
    parts = normalized.split()
    if len(parts) != 5:
        raise CronValidationError(
            f"cron expression must have 5 fields, got {len(parts)}: {expr!r}"
        )
    try:
        schedule = crontab(
            minute=parts[0],
            hour=parts[1],
            day_of_month=parts[2],
            month_of_year=parts[3],
            day_of_week=parts[4],
            nowfun=lambda: reference,
        )
    except (_CeleryParseException, ValueError, KeyError) as exc:
        raise CronValidationError(f"invalid cron expression {expr!r}: {exc}") from exc
    remaining = schedule.remaining_estimate(reference)
    seconds = remaining.total_seconds()
    if seconds <= 0:
        seconds = 60.0
    return reference + timedelta(seconds=seconds)



__all__ = [
    "CronValidationError",
    "next_run_at",
    "parse_cron",
    "validate_cron",
]
