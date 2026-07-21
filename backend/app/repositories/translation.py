"""Repository layer for the multilingual content platform (Phase 5.2).

Thin extensions over :class:`CRUDBase`. Business rules — workflow,
permission checks, uniqueness — live in :mod:`app.services.translation`.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.translation import Translation, TranslationJob, TranslationLocale


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------


class TranslationRepository(CRUDBase[Translation]):
    def __init__(self) -> None:
        super().__init__(Translation)

    # -- Reads ---------------------------------------------------------------

    def get_translation(self, db: Session, translation_id: uuid.UUID | str) -> Translation | None:
        return self.get(db, translation_id)

    def get_scoped(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: uuid.UUID | str,
        locale: str,
        field_name: str,
    ) -> Translation | None:
        stmt = select(Translation).where(
            Translation.entity_type == entity_type,
            Translation.entity_id == entity_id,
            Translation.locale == locale,
            Translation.field_name == field_name,
            Translation.deleted_at.is_(None),
        )
        return db.scalar(stmt)

    def get_translations(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: uuid.UUID | str,
    ) -> list[Translation]:
        return self.list_by_entity(db, entity_type=entity_type, entity_id=entity_id)

    def list_by_entity(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: uuid.UUID | str,
        locale: str | None = None,
    ) -> list[Translation]:
        stmt = select(Translation).where(
            Translation.entity_type == entity_type,
            Translation.entity_id == entity_id,
            Translation.deleted_at.is_(None),
        )
        if locale:
            stmt = stmt.where(Translation.locale == locale)
        stmt = stmt.order_by(Translation.locale.asc(), Translation.field_name.asc())
        return list(db.scalars(stmt))

    def list_by_locale(
        self,
        db: Session,
        *,
        locale: str,
        status: str | None = None,
    ) -> list[Translation]:
        stmt = select(Translation).where(
            Translation.locale == locale,
            Translation.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(Translation.status == status)
        return list(db.scalars(stmt.order_by(Translation.updated_at.desc())))

    def list_by_status(self, db: Session, *, status: str) -> list[Translation]:
        stmt = select(Translation).where(
            Translation.status == status,
            Translation.deleted_at.is_(None),
        )
        return list(db.scalars(stmt.order_by(Translation.updated_at.desc())))

    def published_translation(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: uuid.UUID | str,
        locale: str,
        field_name: str,
    ) -> Translation | None:
        stmt = select(Translation).where(
            Translation.entity_type == entity_type,
            Translation.entity_id == entity_id,
            Translation.locale == locale,
            Translation.field_name == field_name,
            Translation.status == "published",
            Translation.deleted_at.is_(None),
        )
        return db.scalar(stmt)

    # -- Search --------------------------------------------------------------

    def search(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        entity_type: str | None = None,
        entity_id: uuid.UUID | str | None = None,
        locale: str | None = None,
        status: str | None = None,
        field_name: str | None = None,
        translator_id: uuid.UUID | str | None = None,
        reviewer_id: uuid.UUID | str | None = None,
        query: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[Translation], int]:
        stmt = select(Translation).where(Translation.deleted_at.is_(None))
        if entity_type:
            stmt = stmt.where(Translation.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(Translation.entity_id == entity_id)
        if locale:
            stmt = stmt.where(Translation.locale == locale)
        if status:
            stmt = stmt.where(Translation.status == status)
        if field_name:
            stmt = stmt.where(Translation.field_name == field_name)
        if translator_id:
            stmt = stmt.where(Translation.translated_by_user_id == translator_id)
        if reviewer_id:
            stmt = stmt.where(Translation.reviewed_by_user_id == reviewer_id)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Translation.translated_value.ilike(like),
                    Translation.field_name.ilike(like),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(Translation, sort_by):
            col = getattr(Translation, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(Translation.updated_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    # -- Writes --------------------------------------------------------------

    def upsert_translation(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: uuid.UUID | str,
        locale: str,
        field_name: str,
        defaults: dict[str, Any],
    ) -> tuple[Translation, bool]:
        """Insert or update by (entity_type, entity_id, locale, field_name).

        Returns ``(row, created)``.
        """
        existing = self.get_scoped(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            locale=locale,
            field_name=field_name,
        )
        if existing is not None:
            self.update(db, existing, defaults)
            return existing, False
        data = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "locale": locale,
            "field_name": field_name,
            **defaults,
        }
        return self.create(db, data), True

    def delete_translation(self, db: Session, obj: Translation) -> None:
        self.soft_delete(db, obj)


# ---------------------------------------------------------------------------
# TranslationJob
# ---------------------------------------------------------------------------


class TranslationJobRepository(CRUDBase[TranslationJob]):
    def __init__(self) -> None:
        super().__init__(TranslationJob)

    def create_job(self, db: Session, data: dict[str, Any]) -> TranslationJob:
        return self.create(db, data)

    def get_job(self, db: Session, job_id: uuid.UUID | str) -> TranslationJob | None:
        return self.get(db, job_id)

    def list_jobs(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        entity_type: str | None = None,
        entity_id: uuid.UUID | str | None = None,
        status: str | None = None,
        target_locale: str | None = None,
        requested_by_user_id: uuid.UUID | str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[TranslationJob], int]:
        stmt = select(TranslationJob).where(TranslationJob.deleted_at.is_(None))
        if entity_type:
            stmt = stmt.where(TranslationJob.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(TranslationJob.entity_id == entity_id)
        if status:
            stmt = stmt.where(TranslationJob.status == status)
        if target_locale:
            stmt = stmt.where(TranslationJob.target_locale == target_locale)
        if requested_by_user_id:
            stmt = stmt.where(
                TranslationJob.requested_by_user_id == requested_by_user_id
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(TranslationJob, sort_by):
            col = getattr(TranslationJob, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(TranslationJob.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def update_job(
        self, db: Session, job: TranslationJob, data: dict[str, Any]
    ) -> TranslationJob:
        return self.update(db, job, data)

    def cancel_job(self, db: Session, job: TranslationJob) -> TranslationJob:
        return self.update(db, job, {"status": "cancelled"})


# ---------------------------------------------------------------------------
# TranslationLocale
# ---------------------------------------------------------------------------


class TranslationLocaleRepository(CRUDBase[TranslationLocale]):
    def __init__(self) -> None:
        super().__init__(TranslationLocale)

    def list_locales(
        self, db: Session, *, enabled_only: bool = False
    ) -> list[TranslationLocale]:
        stmt = select(TranslationLocale).where(
            TranslationLocale.deleted_at.is_(None)
        )
        if enabled_only:
            stmt = stmt.where(TranslationLocale.enabled.is_(True))
        stmt = stmt.order_by(
            TranslationLocale.sort_order.asc(), TranslationLocale.locale.asc()
        )
        return list(db.scalars(stmt))

    def enabled_locales(self, db: Session) -> list[TranslationLocale]:
        return self.list_locales(db, enabled_only=True)

    def get_default_locale(self, db: Session) -> TranslationLocale | None:
        stmt = select(TranslationLocale).where(
            TranslationLocale.default_locale.is_(True),
            TranslationLocale.deleted_at.is_(None),
        )
        return db.scalar(stmt)

    def get_locale(self, db: Session, locale: str) -> TranslationLocale | None:
        stmt = select(TranslationLocale).where(
            TranslationLocale.locale == locale,
            TranslationLocale.deleted_at.is_(None),
        )
        return db.scalar(stmt)

    def clear_default(self, db: Session) -> int:
        rows = list(
            db.scalars(
                select(TranslationLocale).where(
                    TranslationLocale.default_locale.is_(True),
                    TranslationLocale.deleted_at.is_(None),
                )
            )
        )
        for row in rows:
            row.default_locale = False
        if rows:
            db.commit()
        return len(rows)


translations = TranslationRepository()
translation_jobs = TranslationJobRepository()
translation_locales = TranslationLocaleRepository()


__all__ = [
    "TranslationRepository",
    "TranslationJobRepository",
    "TranslationLocaleRepository",
    "translations",
    "translation_jobs",
    "translation_locales",
]
