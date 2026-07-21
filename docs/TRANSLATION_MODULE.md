# Translation Module

_Phase 5 — Multilingual Content Platform. Backend + frontend, delivered
through Phases 5.1–5.6 and accepted at 5.6._

## Architecture

The Translation Platform is a **polymorphic per-entity translation store**
plus a lightweight **job tracker** and **locale registry**. It follows the
same layered conventions as Volunteer, Disaster, and Public Information:

```text
routers  (thin)           app/api/v1/translations.py
services (business logic) app/services/translation.py
events   (side effects)   app/services/translation_events.py
repos    (data access)    app/repositories/translation.py
models   (ORM)            app/models/translation.py
schemas  (I/O contracts)  app/schemas/translation.py
constants                 app/constants/translation.py
```

Routers are marshalling-only; workflow, validation, RBAC, uniqueness, and
side effects live in the service layer.

## Supported Entities

Translations are attached to any parent entity via `(entity_type, entity_id)`
— no database-level FK, integrity enforced in the service layer. Currently
supported entity types (`app/constants/translation.py::SUPPORTED_ENTITY_TYPES`):

- `disaster`
- `public_resource`
- `campaign`
- `organization`

Add a new entity type by appending to `SUPPORTED_ENTITY_TYPES` and the
matching `TRANSLATION_ENTITY_TYPES` in `src/types/translation.ts`.

## Workflow

Translation status is a strict state machine:

```text
draft ──▶ translated ──▶ reviewed ──▶ published
                    └──▶ rejected (from any non-published state)
```

Transitions are enforced by `translation.transition_status` and surface as
`409 Conflict` on invalid moves.

Job status mirrors the standard job lifecycle:
`pending → processing → completed | failed | cancelled`.

## RBAC

Permission checks are enforced in the service layer via `require_perm`:

| Action                          | Required Permission          |
| ------------------------------- | ---------------------------- |
| List / read translations, jobs  | `translation:read`           |
| Create / update translation     | `translation:write`          |
| Review (translated → reviewed)  | `translation:review`         |
| Publish / reject                | `translation:publish`        |
| Locale management               | `translation:manage_locales` |

Roles `translator`, `reviewer`, and existing admin roles are seeded with
the appropriate permission bundles.

## API Summary

Mounted at `/api/v1/translations` (17 paths).

Translations:

- `GET  /translations` — paginated list (filters: entity, locale, status, field, search)
- `POST /translations` — create
- `GET  /translations/{id}` — detail
- `PATCH /translations/{id}` — partial update
- `DELETE /translations/{id}` — soft delete
- `POST /translations/{id}/transition` — status transition
- `GET  /translations/entity/{entity_type}/{entity_id}` — all translations for an entity

Jobs:

- `GET  /translations/jobs` — paginated list
- `POST /translations/jobs` — request
- `GET  /translations/jobs/{id}` — detail
- `POST /translations/jobs/{id}/start|complete|fail|cancel` — lifecycle

Locales:

- `GET  /translations/locales` — list (optional `enabled_only`)
- `POST /translations/locales` — register
- `PATCH /translations/locales/{id}` — update
- `POST /translations/locales/{id}/enable|disable|set-default`

The legacy AI free-text tool remains at `/api/v1/translation` (singular)
and is unaffected.

## Frontend Overview

Reuses the shared design system, TanStack Query, and route-level RBAC.

Routes (`src/routes/_authenticated/`):

- `translations.tsx` — layout with tab nav (Translations / Jobs / Locales)
- `translations.index.tsx` — list + filters + pagination
- `translations.$id.tsx` — detail, edit, review, publish, reject
- `translations.jobs.tsx` — jobs list + request dialog
- `translations.locales.tsx` — locale registry management
- `translations.entity.$entityType.$entityId.tsx` — per-entity panel (deep-link from Disaster / Public Resource / Organization / Campaign)

Components (`src/components/translations/`):

- `entity-translations-panel.tsx`
- `translation-editor-dialog.tsx`
- `job-request-dialog.tsx`
- `locale-form-dialog.tsx`
- `translation-badges.tsx`

Service + typing:

- `src/services/translation.service.ts` — API wrapper (legacy free-text methods preserved)
- `src/types/translation.ts` — platform + legacy types
- `src/lib/queryKeys.ts` — centralised keys for stable invalidation

Loading, empty, and error states use the shared `data-table`,
`empty-state`, and `error-boundary` primitives — no bespoke UI.

## Search Integration

The `translation` scope is registered in `app/services/search.py`.
Queries support filtering by entity, locale, field, status, and free-text
match against `translated_value`. Results are gated by
`translation:read`.

## Audit Integration

Every mutating router (`translations`, `translation_jobs`,
`translation_locales`) emits an `audit.log` entry with the acting user,
module, action verb, and target ID. Read endpoints are not audited by
design.

## Notification Integration

`app/services/translation_events.py` emits notifications for:

- Translation: `created`, `updated`, `reviewed`, `published`, `rejected`, `deleted`
- Job: `requested`, `started`, `completed`, `failed`, `cancelled`
- Locale: `registered`, `enabled`, `disabled`, `default_changed`

All emitters wrap `notification.create` in `_safe_create` so a failure in
the notification pipeline never rolls back the business transaction.

## Limitations

- No AI/MT provider integration — jobs are records only.
- No bulk import/export (CSV / XLIFF).
- No cache-busting hook for public pages on `published` transitions.
- Per-entity FK integrity is service-enforced, not database-enforced.

## Future — AI Provider Integration

The `TranslationJob` model already carries a `provider` field and
`metadata` JSONB. A future phase can:

1. Register providers (OpenAI, DeepL, Google) in a `providers` module.
2. On `job.request`, dispatch a Celery task that calls the provider and
   writes back an `EntityTranslation(status="translated")`.
3. Update job status via the existing lifecycle endpoints.
4. Surface provider selection + progress in `job-request-dialog.tsx`.

No schema changes are required for this path.
