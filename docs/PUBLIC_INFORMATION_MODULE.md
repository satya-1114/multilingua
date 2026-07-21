# Public Information & QR Module

Status: **Complete** (Phases 4.1 – 4.6).

The module lets operators publish shareable resource pages (disasters,
campaigns, recruitment drives, emergency info, donations, organization
profiles) addressable by human-friendly slug and by opaque QR token, and
records anonymous view analytics for each page.

## Architecture

```
                 ┌──────────────────────────┐
                 │  Frontend (TanStack)     │
                 │  /public-resources/*     │  (authenticated management)
                 │  /p/:slug, /q/:token     │  (anonymous landing)
                 └────────────┬─────────────┘
                              │  httpClient / apiService
                              ▼
   ┌─────────────────────────────────────────────────┐
   │  FastAPI                                         │
   │  /api/v1/public-resources  (auth, RBAC-guarded) │
   │  /api/public/*             (anonymous)          │
   └────────────┬─────────────────────────┬──────────┘
                │                         │
                ▼                         ▼
        services/public_access     services/public_access_events
                │                         │
                ▼                         ▼
      repositories/public_access   notifications + audit + search
                │
                ▼
        SQLAlchemy models (public_access.py)
```

## Models (`backend/app/models/public_access.py`)

- `PublicResource` — polymorphic pointer (`resource_type` + optional
  `resource_id`) with `slug`, `qr_token`, `visibility`, `expires_at`,
  optional `organization_id`, `created_by_user_id`, and a free-form
  `metadata` JSONB blob. Unique constraints on `slug` and `qr_token`.
- `QRCode` — metadata for generated QR artifacts (`format`, `version`,
  `status`, `generated_at`, `metadata`). Binary bytes are not stored.
- `PublicView` — anonymous access log with SHA-256 hashed IP / user agent,
  ISO country, device type, and referrer.

Migration: `backend/alembic/versions/0004_public_access.py`.

## Repositories (`backend/app/repositories/public_access.py`)

`PublicResourceRepository`, `QRCodeRepository`, `PublicViewRepository`
extend `CRUDBase`. They expose scoped queries (by slug, by QR token,
by resource pointer, recent views, summary counts).

## Services

### `services/public_access.py`

- CRUD for public resources with slug + QR token uniqueness enforcement.
- Lifecycle actions: `publish`, `expire`, `disable`, `regenerate_qr_token`.
- Visibility rules (`public`, `unlisted`, `private`, `expired`, `disabled`)
  and future-only `expires_at` validation.
- QR metadata registration + status transitions.
- Anonymous resolution by slug or QR token with expiry enforcement.
- `register_view` with SHA-256 IP/UA hashing and 30-second duplicate
  suppression per (resource, ip_hash).

### `services/public_access_events.py`

Emits notification bus events for `resource.created`, `resource.updated`,
`resource.published`, `resource.expired`, `resource.disabled`,
`resource.qr_regenerated`, and `qr.registered`.

## API

### Authenticated — `/api/v1/public-resources`

Registered in `backend/app/api/router.py`. All routes require
`PUBLIC_MANAGE` (or `PUBLIC_VIEW` for reads); QR routes require
`QR_MANAGE`.

- `GET    /public-resources` — paginated list with search / filters.
- `POST   /public-resources` — create.
- `GET    /public-resources/{id}` — detail.
- `PATCH  /public-resources/{id}` — update.
- `DELETE /public-resources/{id}` — soft delete.
- `POST   /public-resources/{id}/publish`
- `POST   /public-resources/{id}/expire`
- `POST   /public-resources/{id}/disable`
- `POST   /public-resources/{id}/regenerate-qr`
- `GET    /public-resources/{id}/qr` — list QR metadata rows.
- `POST   /public-resources/{id}/qr` — register a QR metadata row.
- `PATCH  /public-resources/{id}/qr/{qrId}` — update status/metadata.
- `GET    /public-resources/{id}/views` — recent views (paginated).
- `GET    /public-resources/{id}/views/summary` — aggregate counts.

### Anonymous — `/api/public`

Mounted in `backend/main.py`.

- `GET  /api/public/resources/by-slug/{slug}` — resolve slug.
- `GET  /api/public/resources/by-token/{token}` — resolve QR token.
- `POST /api/public/resources/{id}/views` — log a view (hashed IP/UA).

Both resolution endpoints return `404` for missing, expired, or disabled
resources.

## RBAC (`src/constants/rbac.ts` + `backend/app/security/rbac.py`)

| Permission     | Roles                                                                   |
| -------------- | ----------------------------------------------------------------------- |
| `PUBLIC_VIEW`  | Super Admin, Campaign Manager, Volunteer, Viewer                        |
| `PUBLIC_MANAGE`| Super Admin, Campaign Manager                                           |
| `QR_MANAGE`    | Super Admin, Campaign Manager                                           |

## Notification Events

Emitted through `services/public_access_events.py`:
`public_resource.created`, `public_resource.updated`,
`public_resource.published`, `public_resource.expired`,
`public_resource.disabled`, `public_resource.qr_regenerated`,
`public_resource.qr_registered`.

## Audit Events

Every state-changing endpoint calls `AuditService.log` with the acting
user, resource id, and a serialized diff of before/after fields.

## Search Integration

Registered scope: `public_resource`. Indexes `title`, `slug`, `description`
and filters by `visibility` and `resource_type`.

## Frontend

### Pages
- `src/routes/_authenticated/public-resources.index.tsx` — list with
  server-side pagination, search, filters, empty/error/loading states.
- `src/routes/_authenticated/public-resources.new.tsx` — creation form
  with slug pattern validation.
- `src/routes/_authenticated/public-resources.$id.tsx` — management
  detail: metadata, lifecycle actions, QR list, view history + summary.
- `src/routes/p.$slug.tsx` — anonymous landing by slug, auto-registers
  a view on mount.
- `src/routes/q.$token.tsx` — anonymous landing by QR token, reuses the
  same view component.

### Service + types
- `src/services/public-access.service.ts` — thin façade over `apiService`
  for management endpoints and absolute-URL calls to `/api/public/*` for
  anonymous resolution.
- `src/types/public-access.ts` — DTOs and enum constants (single source
  of truth for `RESOURCE_TYPES`, `VISIBILITIES`, `QR_STATUSES`,
  `QR_FORMATS`).

### TanStack Query keys
- `["public-resources"]` — list root.
- `["public-resources", "list", query]` — paginated list.
- `["public-resources", id]` — resource detail.
- `["public-resources", id, "qr"]` — QR metadata.
- `["public-resources", id, "views"]` — recent views.
- `["public-resources", id, "views", "summary"]` — summary counts.
- `["public", "slug", slug]` / `["public", "token", token]` — anonymous
  resolution.

## Known Deferred Features

- QR image generation (PNG/SVG/PDF rendering).
- Short-URL / redirect service.
- Analytics dashboard (charts over `PublicView`).
- Automation triggers reacting to public resource lifecycle events.
- Multilingual translation of resource titles/descriptions (handled by
  the pending Multilingual Content module).
