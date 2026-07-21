# Disaster Management Module

Reference documentation for the Disaster module delivered in Phases 3.1–3.6.

## Architecture Overview

Layered backend following the existing platform conventions:

```
Router (app/api/v1/disasters.py)
  → Service (app/services/disaster.py, disaster_events.py)
    → Repository (app/repositories/disaster.py)
      → SQLAlchemy Models (app/models/disaster.py)
```

Cross-cutting integrations:
- **Notifications** — `app/services/disaster_events.py` publishes lifecycle events via the existing notification bus.
- **Audit** — every mutating API endpoint calls `audit.log(...)`.
- **Search** — `disaster` and `assignment` scopes registered in `app/services/search.py`.
- **RBAC** — permissions declared in `app/security/rbac.py` and enforced in the router via existing dependencies.

Frontend follows the standard `apiService` + `httpClient` + TanStack Query pattern, wired into `src/services/disaster.service.ts` and consumed by the routes under `src/routes/_authenticated/disasters.*.tsx`.

## Database Model Summary

Migration: `backend/alembic/versions/0003_disasters.py`.

| Table                    | Purpose                                                   | Key Fields                                                                                   |
| ------------------------ | --------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `disasters`              | Incident record.                                          | `id`, `title`, `description`, `type`, `severity`, `status`, `started_at`, `resolved_at`, `latitude`, `longitude`, `address`, `city`, `state`, `country`, `postal_code`, soft-delete + audit columns. |
| `disaster_assignments`   | Volunteer/organization deployment to a disaster.          | `id`, `disaster_id`, `volunteer_id`, `organization_id`, `role`, `status`, `notes`, timestamps. |
| `disaster_attachments`   | Metadata for related documents/images.                    | `id`, `disaster_id`, `kind`, `filename`, `mime_type`, `size_bytes`, `url`, `uploaded_by`.    |

Enums live in `app/constants/disaster.py`: `DisasterType`, `DisasterSeverity`, `DisasterStatus`, `AssignmentStatus`, `AttachmentKind`.

## State Machines

Defined in `app/constants/disaster.py`.

**Disaster status:**
```
draft → reported → verified → active → contained → resolved → closed
                                         ↑            ↓
                                     (reopen from closed → active)
```
Illegal transitions raise `InvalidStateTransition`.

**Assignment status:**
```
pending → accepted → in_progress → completed
       ↘ declined
       ↘ cancelled  (allowed from pending / accepted / in_progress)
```

## RBAC Permissions

Declared in `app/security/rbac.py`.

- `disaster:view`, `disaster:create`, `disaster:update`, `disaster:delete`
- `disaster:verify`, `disaster:activate`, `disaster:contain`, `disaster:resolve`, `disaster:close`, `disaster:reopen`
- `assignment:view`, `assignment:create`, `assignment:update`, `assignment:delete`, `assignment:reassign`, `assignment:status`
- `attachment:view`, `attachment:create`, `attachment:delete`

## API Endpoints

All under `/api/v1/disasters` (see `app/api/v1/disasters.py`).

**Disasters**
- `GET /` — list with filters (type, severity, status, state, search, pagination).
- `POST /` — create.
- `GET /{id}` — detail.
- `PATCH /{id}` — update.
- `DELETE /{id}` — soft delete.
- `POST /{id}/verify | /activate | /contain | /resolve | /close | /reopen` — lifecycle transitions.

**Assignments**
- `GET /{id}/assignments`
- `POST /{id}/assignments`
- `PATCH /{id}/assignments/{assignment_id}`
- `POST /{id}/assignments/{assignment_id}/reassign`
- `POST /{id}/assignments/{assignment_id}/status`
- `DELETE /{id}/assignments/{assignment_id}`

**Attachments** (metadata only; binary storage deferred)
- `GET /{id}/attachments`
- `POST /{id}/attachments`
- `DELETE /{id}/attachments/{attachment_id}`

## Frontend Pages

Under `src/routes/_authenticated/`:
- `disasters.index.tsx` — filterable, paginated list.
- `disasters.new.tsx` / `disasters.$id.edit.tsx` — create/update forms.
- `disasters.$id.index.tsx` — detail view with lifecycle actions, Assignments tab, Attachments tab.

Shared UI: `src/components/common/disaster-badges.tsx`, `disaster-form.tsx`.

## Notification Events

Emitted from `app/services/disaster_events.py`:
- `disaster.created`, `disaster.updated`, `disaster.deleted`
- `disaster.verified`, `disaster.activated`, `disaster.contained`, `disaster.resolved`, `disaster.closed`, `disaster.reopened`
- `disaster.assignment.created`, `disaster.assignment.updated`, `disaster.assignment.reassigned`, `disaster.assignment.status_changed`, `disaster.assignment.deleted`

Failures are swallowed so business logic is never blocked by notification issues.

## Audit Events

Every mutating router action logs via `audit.log(action, resource, resource_id, metadata)` — CRUD, lifecycle transitions, assignment operations, and attachment operations.

## Search Integration

Registered in `app/services/search.py`:
- `disaster` scope — searches `title`, `address`, city/state/country fields; gated by `disaster:view`.
- `assignment` scope — searches `role`, `notes`; gated by `assignment:view`.

## Known Future Enhancements (Deferred)

- **Attachment binary storage** — currently metadata-only; add S3/local storage + signed URL flow.
- **Public alert pages** — `src/routes/public.alerts.$slug.tsx` is a placeholder; requires public read API + slug routing.
- **Maps** — expose lat/lon on an interactive map (list + detail).
- **Analytics** — dedicated disaster dashboards (by type/severity/geography).
- **Automation** — trigger workflows on lifecycle transitions.
- **QR code issuance** — for verified public disasters.
- **Bulk import / API tokens for field devices.**
