# Milestone 2 — Volunteer Management: Backend Requirements

The frontend Volunteer Management module is fully implemented against the
existing `apiService` HTTP layer. The following endpoints, permissions, and
database entities need to be provided by the FastAPI backend.

## Permissions to seed

Add these permissions to the RBAC seed and grant them to the roles listed:

| Permission          | Roles                                          |
| ------------------- | ---------------------------------------------- |
| `volunteer:view`    | Super Admin, Campaign Manager                  |
| `volunteer:manage`  | Super Admin, Campaign Manager                  |
| `task:view`         | Super Admin, Campaign Manager, Volunteer       |
| `task:assign`       | Super Admin, Campaign Manager                  |
| `task:manage`       | Super Admin, Campaign Manager                  |
| `task:act`          | Volunteer (accept / reject / progress own)     |

## REST endpoints

All routes are under the existing `/api/v1` prefix and use the standard
envelope `{ data, meta }` already implemented by `httpClient`.

### Volunteers

- `GET /volunteers`
  Query params: `search`, `language`, `skill`, `location`, `availability`,
  `status`, `taskStatus`, `sortBy`, `sortDir`, `page`, `pageSize`.
  Returns `Paginated<Volunteer>`.
  Requires `volunteer:view`.

- `GET /volunteers/:id`
  Returns a single `Volunteer`. Requires `volunteer:view`.

- `GET /volunteers/:id/tasks`
  Returns `VolunteerTask[]` for the volunteer. Requires `volunteer:view`.

- `PATCH /volunteers/:id`
  Body: `{ status?, ...profile fields }`. Requires `volunteer:manage`.

### Tasks

- `GET /tasks`
  Query params: `volunteerId`, `campaignId`, `status`, `priority`,
  `search`, `page`, `pageSize`. Requires `task:view`.

- `GET /tasks/mine`
  Returns `VolunteerTask[]` for the authenticated volunteer.
  Requires `task:view` + `task:act`.

- `POST /tasks`
  Body: `{ volunteerId, campaignId, title, description, priority, dueAt? }`.
  Creates a task in `pending` status. Requires `task:assign`.

- `PATCH /tasks/:id`
  Edit assignment fields (`title`, `description`, `priority`, `dueAt`,
  `campaignId`). Requires `task:manage`.

- `PATCH /tasks/:id/status`
  Body: `{ status }`. Transitions:
  - `pending → accepted | rejected` (volunteer via `task:act`)
  - `accepted → in_progress` (volunteer)
  - `in_progress → completed` (volunteer)
  - Campaign Manager may force any transition via `task:manage`.

- `DELETE /tasks/:id`
  Cancels an assignment (soft delete → `status = cancelled`).
  Requires `task:manage`.

## Database tables

### `volunteers`

| Column               | Type          | Notes                                  |
| -------------------- | ------------- | -------------------------------------- |
| `id`                 | uuid PK       |                                        |
| `user_id`            | uuid FK users | unique, one profile per user           |
| `languages`          | text[]        | ISO language codes                     |
| `skills`             | text[]        |                                        |
| `current_location`   | text          |                                        |
| `availability`       | text          | e.g. Weekdays / Weekends / Full-time   |
| `status`             | text          | `available | busy | on_leave | inactive` |
| `created_at`         | timestamptz   |                                        |
| `updated_at`         | timestamptz   |                                        |

The registration payload already collects `languagesKnown`, `skills`,
`currentLocation`, `availability` for role `volunteer`; the auth service
should upsert a `volunteers` row on registration.

### `volunteer_tasks`

| Column          | Type        | Notes                                          |
| --------------- | ----------- | ---------------------------------------------- |
| `id`            | uuid PK     |                                                |
| `volunteer_id`  | uuid FK     | → volunteers.id                                |
| `campaign_id`   | uuid FK     | → campaigns.id                                 |
| `title`         | text        |                                                |
| `description`   | text        |                                                |
| `priority`      | text        | `low | medium | high | urgent`                 |
| `status`        | text        | `pending | accepted | in_progress | completed | rejected | cancelled` |
| `assigned_at`   | timestamptz | default `now()`                                |
| `due_at`        | timestamptz | nullable                                       |
| `completed_at`  | timestamptz | nullable                                       |
| `created_by`    | uuid FK     | → users.id (Campaign Manager)                  |
| `updated_at`    | timestamptz |                                                |

Add indexes on (`volunteer_id`, `status`) and (`campaign_id`, `status`).

## Migration suggestions

1. Create the two tables above.
2. Backfill `volunteers` for every existing user with `role = 'volunteer'`.
3. Seed the six new permissions and attach them to the four roles as per
   the matrix above (mirror `src/constants/rbac.ts`).
4. Emit `volunteer.task.assigned` / `volunteer.task.status_changed` events
   into the existing notification pipeline so volunteers get in-app alerts.

## Conflicts with existing architecture

None. The module uses the existing `apiService` facade, `PermissionGuard`,
`DataTable`, `StatusBadge`, `StatCard`, `SectionHeader`, `EmptyState`,
`ErrorState`, `SkeletonBlock`, and `ConfirmDialog` components; no
services or routes were replaced.
