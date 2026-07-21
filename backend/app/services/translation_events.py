"""Translation platform domain-event emitters.

Thin adapter that translates Translation / TranslationJob / TranslationLocale
business events into the existing :mod:`app.services.notifications` pipeline.
Kept isolated from the core service so business logic remains pure and
testable, and so future channels (email, push, SMS) can be added here
without touching the service layer.

All emitters swallow errors: a notification failure MUST NOT abort the
underlying business operation. Errors are logged.
"""
from __future__ import annotations

import uuid
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.translation import Translation, TranslationJob, TranslationLocale
from app.services import notifications as notif_service

log = get_logger(__name__)

CATEGORY = "translation"


def _safe_create(db: Session, *, user_id: uuid.UUID | str | None, **kwargs: Any) -> None:
    if user_id is None:
        return
    if not isinstance(user_id, uuid.UUID):
        try:
            user_id = uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            return
    try:
        notif_service.create(db, user_id=user_id, category=CATEGORY, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("translation notification emit failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass


def _label(t: Translation) -> str:
    return f"{t.entity_type}:{t.field_name} [{t.locale}]"


def _href(t: Translation) -> str:
    return f"/translations/{t.id}"


def _job_label(j: TranslationJob) -> str:
    return f"{j.entity_type} → {j.target_locale}"


def _job_href(j: TranslationJob) -> str:
    return f"/translations/jobs/{j.id}"


def _recipients(t: Translation) -> list[uuid.UUID | None]:
    """Return unique translator / reviewer IDs to notify."""
    out: list[uuid.UUID | None] = []
    for uid in (t.translated_by_user_id, t.reviewed_by_user_id):
        if uid is not None and uid not in out:
            out.append(uid)
    return out


# ---------------------------------------------------------------------------
# Translation lifecycle
# ---------------------------------------------------------------------------


def translation_created(db: Session, t: Translation) -> None:
    _safe_create(
        db,
        user_id=t.translated_by_user_id,
        title=f"Translation created: {_label(t)}",
        message="A new translation entry has been created.",
        priority="low",
        href=_href(t),
    )


def translation_updated(db: Session, t: Translation) -> None:
    for uid in _recipients(t):
        _safe_create(
            db,
            user_id=uid,
            title=f"Translation updated: {_label(t)}",
            message="A translation entry has been updated.",
            priority="low",
            href=_href(t),
        )


def translation_reviewed(db: Session, t: Translation) -> None:
    _safe_create(
        db,
        user_id=t.translated_by_user_id,
        title=f"Translation approved: {_label(t)}",
        message="Your translation has been reviewed and approved.",
        priority="normal",
        href=_href(t),
    )


def translation_published(db: Session, t: Translation) -> None:
    for uid in _recipients(t):
        _safe_create(
            db,
            user_id=uid,
            title=f"Translation published: {_label(t)}",
            message="This translation is now live.",
            priority="normal",
            href=_href(t),
        )


def translation_rejected(db: Session, t: Translation) -> None:
    _safe_create(
        db,
        user_id=t.translated_by_user_id,
        title=f"Translation rejected: {_label(t)}",
        message="Your translation was sent back to draft for revision.",
        priority="high",
        href=_href(t),
    )


def translation_deleted(db: Session, t: Translation) -> None:
    _safe_create(
        db,
        user_id=t.translated_by_user_id,
        title=f"Translation deleted: {_label(t)}",
        message="A translation entry has been deleted.",
        priority="low",
        href=_href(t),
    )


# ---------------------------------------------------------------------------
# Translation Job lifecycle
# ---------------------------------------------------------------------------


def job_requested(db: Session, j: TranslationJob) -> None:
    _safe_create(
        db,
        user_id=j.requested_by_user_id,
        title=f"Translation job requested: {_job_label(j)}",
        message="Your translation job has been queued.",
        priority="low",
        href=_job_href(j),
    )


def job_started(db: Session, j: TranslationJob) -> None:
    _safe_create(
        db,
        user_id=j.requested_by_user_id,
        title=f"Translation job started: {_job_label(j)}",
        message="Your translation job is now processing.",
        priority="low",
        href=_job_href(j),
    )


def job_completed(db: Session, j: TranslationJob) -> None:
    _safe_create(
        db,
        user_id=j.requested_by_user_id,
        title=f"Translation job completed: {_job_label(j)}",
        message="Your translation job has completed successfully.",
        priority="normal",
        href=_job_href(j),
    )


def job_failed(db: Session, j: TranslationJob) -> None:
    _safe_create(
        db,
        user_id=j.requested_by_user_id,
        title=f"Translation job failed: {_job_label(j)}",
        message="Your translation job failed. See job details for the error.",
        priority="high",
        href=_job_href(j),
    )


def job_cancelled(db: Session, j: TranslationJob) -> None:
    _safe_create(
        db,
        user_id=j.requested_by_user_id,
        title=f"Translation job cancelled: {_job_label(j)}",
        message="Your translation job was cancelled.",
        priority="low",
        href=_job_href(j),
    )


# ---------------------------------------------------------------------------
# Locale lifecycle
# ---------------------------------------------------------------------------
#
# Locale changes are workspace-wide operations with no natural single-user
# recipient. We provide emitters for symmetry with the audit trail and to
# support future broadcast channels; today they no-op unless a caller
# passes an explicit ``notify_user_ids`` iterable.


def _broadcast(
    db: Session,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None,
    *,
    title: str,
    message: str,
    priority: str = "low",
    href: str = "/translations/locales",
) -> None:
    for uid in notify_user_ids or ():
        _safe_create(
            db, user_id=uid, title=title, message=message,
            priority=priority, href=href,
        )


def locale_registered(
    db: Session,
    locale: TranslationLocale,
    *,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, notify_user_ids,
        title=f"Locale registered: {locale.locale}",
        message=f"{locale.display_name} is now available.",
    )


def locale_enabled(
    db: Session,
    locale: TranslationLocale,
    *,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, notify_user_ids,
        title=f"Locale enabled: {locale.locale}",
        message=f"{locale.display_name} translations can now be authored.",
    )


def locale_disabled(
    db: Session,
    locale: TranslationLocale,
    *,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, notify_user_ids,
        title=f"Locale disabled: {locale.locale}",
        message=f"{locale.display_name} is no longer accepting new translations.",
    )


def locale_default_changed(
    db: Session,
    locale: TranslationLocale,
    *,
    notify_user_ids: Iterable[uuid.UUID | str | None] | None = None,
) -> None:
    _broadcast(
        db, notify_user_ids,
        title=f"Default locale changed: {locale.locale}",
        message=f"{locale.display_name} is now the platform default locale.",
        priority="normal",
    )


__all__ = [
    "CATEGORY",
    "translation_created",
    "translation_updated",
    "translation_reviewed",
    "translation_published",
    "translation_rejected",
    "translation_deleted",
    "job_requested",
    "job_started",
    "job_completed",
    "job_failed",
    "job_cancelled",
    "locale_registered",
    "locale_enabled",
    "locale_disabled",
    "locale_default_changed",
]
