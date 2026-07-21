"""Multilingual content platform routes (Phase 5.3).

Thin FastAPI layer over :mod:`app.services.translation` platform services.
All validation, workflow, RBAC, and uniqueness rules live in the service
layer — routers only marshal request/response and pagination envelopes.

The legacy AI free-text translation router lives at ``/translation``
(singular) and remains unchanged.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.responses import ok, paginated
from app.dependencies.auth import current_user
from app.dependencies.db import get_db
from app.models.translation import Translation, TranslationJob, TranslationLocale
from app.models.user import User
from app.schemas.translation import (
    EntityTranslationCreate,
    EntityTranslationUpdate,
    TranslationJobCreate,
    TranslationLocaleCreate,
    TranslationLocaleUpdate,
)
from app.services import audit, translation as svc

router = APIRouter()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt is not None else None


def _roles(user: User) -> list[str]:
    return [r.name for r in getattr(user, "roles", []) or []]


def _serialize_translation(t: Translation) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "entityType": t.entity_type,
        "entityId": str(t.entity_id),
        "locale": t.locale,
        "fieldName": t.field_name,
        "translatedValue": t.translated_value,
        "status": t.status,
        "sourceHash": t.source_hash,
        "translatedByUserId": str(t.translated_by_user_id) if t.translated_by_user_id else None,
        "reviewedByUserId": str(t.reviewed_by_user_id) if t.reviewed_by_user_id else None,
        "metadata": dict(t.metadata_ or {}),
        "createdAt": _iso(t.created_at),
        "updatedAt": _iso(t.updated_at),
    }


def _serialize_job(j: TranslationJob) -> dict[str, Any]:
    return {
        "id": str(j.id),
        "entityType": j.entity_type,
        "entityId": str(j.entity_id),
        "sourceLocale": j.source_locale,
        "targetLocale": j.target_locale,
        "status": j.status,
        "provider": j.provider,
        "requestedByUserId": str(j.requested_by_user_id) if j.requested_by_user_id else None,
        "requestedAt": _iso(j.requested_at),
        "completedAt": _iso(j.completed_at),
        "metadata": dict(j.metadata_ or {}),
        "createdAt": _iso(j.created_at),
        "updatedAt": _iso(j.updated_at),
    }


def _serialize_locale(l: TranslationLocale) -> dict[str, Any]:
    return {
        "id": str(l.id),
        "locale": l.locale,
        "displayName": l.display_name,
        "nativeName": l.native_name,
        "rtl": bool(l.rtl),
        "enabled": bool(l.enabled),
        "defaultLocale": bool(l.default_locale),
        "sortOrder": int(l.sort_order),
        "createdAt": _iso(l.created_at),
        "updatedAt": _iso(l.updated_at),
    }


# --------------------------------------------------------------------------- #
# Locale routes  (registered before /{translation_id})
# --------------------------------------------------------------------------- #


@router.get("/locales", response_model=None, summary="List supported locales")
def list_locales(
    enabled_only: bool = Query(False, alias="enabledOnly"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    items = svc.list_locales(db, roles=_roles(user), enabled_only=enabled_only)
    return ok([_serialize_locale(l) for l in items])


@router.post("/locales", status_code=201, response_model=None, summary="Register a locale")
def register_locale(
    payload: TranslationLocaleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = svc.register_locale(
        db, roles=_roles(user), payload=payload.model_dump(exclude_none=True, by_alias=False)
    )
    audit.log(db, action="register", module="translation_locale", actor_id=user.id,
              entity_id=str(row.id), entity_label=row.locale,
              metadata={"displayName": row.display_name})
    return ok(_serialize_locale(row))


@router.patch("/locales/{locale}", response_model=None, summary="Update a locale")
def update_locale(
    locale: str,
    payload: TranslationLocaleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = svc.update_locale(
        db,
        roles=_roles(user),
        locale=locale,
        payload=payload.model_dump(exclude_none=True, by_alias=False),
    )
    audit.log(db, action="update", module="translation_locale", actor_id=user.id,
              entity_id=str(row.id), entity_label=row.locale)
    return ok(_serialize_locale(row))


@router.post("/locales/{locale}/enable", response_model=None, summary="Enable a locale")
def enable_locale(
    locale: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = svc.enable_locale(db, roles=_roles(user), locale=locale)
    audit.log(db, action="enable", module="translation_locale", actor_id=user.id,
              entity_id=str(row.id), entity_label=row.locale)
    return ok(_serialize_locale(row))


@router.post("/locales/{locale}/disable", response_model=None, summary="Disable a locale")
def disable_locale(
    locale: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = svc.disable_locale(db, roles=_roles(user), locale=locale)
    audit.log(db, action="disable", module="translation_locale", actor_id=user.id,
              entity_id=str(row.id), entity_label=row.locale)
    return ok(_serialize_locale(row))


@router.post(
    "/locales/{locale}/set-default", response_model=None, summary="Mark locale as default"
)
def set_default_locale(
    locale: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = svc.set_default_locale(db, roles=_roles(user), locale=locale)
    audit.log(db, action="set_default", module="translation_locale", actor_id=user.id,
              entity_id=str(row.id), entity_label=row.locale)
    return ok(_serialize_locale(row))


# --------------------------------------------------------------------------- #
# Translation job routes  (registered before /{translation_id})
# --------------------------------------------------------------------------- #


@router.get("/jobs", response_model=None, summary="List translation jobs")
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200, alias="pageSize"),
    entity_type: str | None = Query(None, alias="entityType"),
    entity_id: uuid.UUID | None = Query(None, alias="entityId"),
    status: str | None = None,
    target_locale: str | None = Query(None, alias="targetLocale"),
    requested_by_user_id: uuid.UUID | None = Query(None, alias="requestedByUserId"),
    sort_by: str | None = Query(None, alias="sortBy", max_length=64),
    sort_dir: str = Query("desc", alias="sortDir", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    filters = {
        "page": page,
        "page_size": page_size,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "status": status,
        "target_locale": target_locale,
        "requested_by_user_id": requested_by_user_id,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
    }
    items, total = svc.list_jobs(db, roles=_roles(user), filters=filters)
    return paginated([_serialize_job(j) for j in items], page, page_size, total)


@router.post("/jobs", status_code=201, response_model=None, summary="Request a translation job")
def create_job(
    payload: TranslationJobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    job = svc.request_translation(
        db,
        roles=_roles(user),
        requested_by=user.id,
        payload=payload.model_dump(exclude_none=True, by_alias=False),
    )
    audit.log(db, action="create", module="translation_job", actor_id=user.id,
              entity_id=str(job.id), entity_label=f"{job.entity_type}->{job.target_locale}")
    return ok(_serialize_job(job))


@router.get("/jobs/{job_id}", response_model=None, summary="Get a translation job")
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return ok(_serialize_job(svc.get_job(db, roles=_roles(user), job_id=job_id)))


@router.post("/jobs/{job_id}/start", response_model=None, summary="Start a translation job")
def start_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    job = svc.start_job(db, roles=_roles(user), job_id=job_id)
    audit.log(db, action="start", module="translation_job", actor_id=user.id, entity_id=str(job.id))
    return ok(_serialize_job(job))


@router.post("/jobs/{job_id}/complete", response_model=None, summary="Complete a translation job")
def complete_job(
    job_id: uuid.UUID,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    metadata = None
    if isinstance(payload, dict):
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None
    job = svc.complete_job(db, roles=_roles(user), job_id=job_id, metadata=metadata)
    audit.log(db, action="complete", module="translation_job", actor_id=user.id, entity_id=str(job.id))
    return ok(_serialize_job(job))


@router.post("/jobs/{job_id}/fail", response_model=None, summary="Mark a translation job failed")
def fail_job(
    job_id: uuid.UUID,
    payload: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    error = (payload or {}).get("error") if isinstance(payload, dict) else None
    job = svc.fail_job(db, roles=_roles(user), job_id=job_id, error=error)
    audit.log(db, action="fail", module="translation_job", actor_id=user.id,
              entity_id=str(job.id), metadata={"error": error} if error else None)
    return ok(_serialize_job(job))


@router.post("/jobs/{job_id}/cancel", response_model=None, summary="Cancel a translation job")
def cancel_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    job = svc.cancel_job(db, roles=_roles(user), job_id=job_id)
    audit.log(db, action="cancel", module="translation_job", actor_id=user.id, entity_id=str(job.id))
    return ok(_serialize_job(job))


# --------------------------------------------------------------------------- #
# Entity translation lookup
# --------------------------------------------------------------------------- #


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=None,
    summary="List translations for a given entity",
)
def list_entity_translations(
    entity_type: str,
    entity_id: uuid.UUID,
    locale: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    items = svc.get_entity_translations(
        db,
        roles=_roles(user),
        entity_type=entity_type,
        entity_id=entity_id,
        locale=locale,
    )
    return ok([_serialize_translation(t) for t in items])


# --------------------------------------------------------------------------- #
# Translation list / create
# --------------------------------------------------------------------------- #


@router.get("", response_model=None, summary="Search translations")
def list_translations(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200, alias="pageSize"),
    query: str | None = Query(None, max_length=200),
    entity_type: str | None = Query(None, alias="entityType"),
    entity_id: uuid.UUID | None = Query(None, alias="entityId"),
    locale: str | None = None,
    status: str | None = None,
    field_name: str | None = Query(None, alias="fieldName"),
    translator_id: uuid.UUID | None = Query(None, alias="translatorId"),
    reviewer_id: uuid.UUID | None = Query(None, alias="reviewerId"),
    sort_by: str | None = Query(None, alias="sortBy", max_length=64),
    sort_dir: str = Query("desc", alias="sortDir", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    filters = {
        "page": page,
        "page_size": page_size,
        "query": query,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "locale": locale,
        "status": status,
        "field_name": field_name,
        "translator_id": translator_id,
        "reviewer_id": reviewer_id,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
    }
    items, total = svc.search_translations(db, roles=_roles(user), filters=filters)
    return paginated(
        [_serialize_translation(t) for t in items], page, page_size, total
    )


@router.post("", status_code=201, response_model=None, summary="Create a translation")
def create_translation(
    payload: EntityTranslationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.create_translation(
        db,
        roles=_roles(user),
        created_by=user.id,
        payload=payload.model_dump(exclude_none=True, by_alias=False),
    )
    audit.log(db, action="create", module="translation", actor_id=user.id,
              entity_id=str(t.id), entity_label=f"{t.entity_type}:{t.field_name}[{t.locale}]")
    return ok(_serialize_translation(t))


# --------------------------------------------------------------------------- #
# Per-translation routes
# --------------------------------------------------------------------------- #


@router.get("/{translation_id}", response_model=None, summary="Get a translation")
def get_translation(
    translation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return ok(
        _serialize_translation(
            svc.get_translation(db, roles=_roles(user), translation_id=translation_id)
        )
    )


@router.patch("/{translation_id}", response_model=None, summary="Update a translation")
def update_translation(
    translation_id: uuid.UUID,
    payload: EntityTranslationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.update_translation(
        db,
        roles=_roles(user),
        translation_id=translation_id,
        payload=payload.model_dump(exclude_none=True, by_alias=False),
        updated_by=user.id,
    )
    audit.log(db, action="update", module="translation", actor_id=user.id,
              entity_id=str(t.id), entity_label=f"{t.entity_type}:{t.field_name}[{t.locale}]")
    return ok(_serialize_translation(t))


@router.delete("/{translation_id}", response_model=None, summary="Delete a translation")
def delete_translation(
    translation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    svc.delete_translation(db, roles=_roles(user), translation_id=translation_id)
    audit.log(db, action="delete", module="translation", actor_id=user.id,
              entity_id=str(translation_id))
    return ok({"id": str(translation_id), "deleted": True})


@router.post("/{translation_id}/review", response_model=None, summary="Approve a translation")
def review_translation(
    translation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.review_translation(
        db,
        roles=_roles(user),
        translation_id=translation_id,
        reviewer_id=user.id,
        approve=True,
    )
    audit.log(db, action="review", module="translation", actor_id=user.id,
              entity_id=str(t.id))
    return ok(_serialize_translation(t))


@router.post("/{translation_id}/reject", response_model=None, summary="Reject a translation")
def reject_translation(
    translation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.review_translation(
        db,
        roles=_roles(user),
        translation_id=translation_id,
        reviewer_id=user.id,
        approve=False,
    )
    audit.log(db, action="reject", module="translation", actor_id=user.id,
              entity_id=str(t.id))
    return ok(_serialize_translation(t))


@router.post("/{translation_id}/publish", response_model=None, summary="Publish a translation")
def publish_translation(
    translation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    t = svc.publish_translation(
        db, roles=_roles(user), translation_id=translation_id
    )
    audit.log(db, action="publish", module="translation", actor_id=user.id,
              entity_id=str(t.id))
    return ok(_serialize_translation(t))
