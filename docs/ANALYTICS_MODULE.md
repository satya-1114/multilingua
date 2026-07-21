# Analytics & Reporting Module

_Status: Complete (Phases 6.1 – 6.6)._

The Analytics Platform provides polymorphic time-series metrics,
period-based KPI snapshots, and tracked report-generation jobs across
every domain module. It is intentionally generic: `entity_type` +
`entity_id` references let new modules emit and query analytics without
schema changes.

## Architecture

```
FastAPI router  ─►  Service layer  ─►  Repository  ─►  ORM models
                         │
                         ├─► analytics_events (notifications + audit)
                         └─► search registry ("analytics" scope)
```

- Thin routers under `backend/app/api/v1/analytics.py` handle HTTP concerns
  and RBAC only.
- Business logic lives in `backend/app/services/analytics.py`
  (`AnalyticsMetricService`, `AnalyticsSnapshotService`,
  `AnalyticsReportService`).
- Persistence is isolated in `backend/app/repositories/analytics.py`.
- Domain events fan out via `backend/app/services/analytics_events.py` to
  the notification bus and audit log.

## Data Model

Three tables (migration `0006_analytics`):

| Table                 | Purpose                                                     |
| --------------------- | ----------------------------------------------------------- |
| `analytics_metrics`   | Polymorphic time-series metric points.                      |
| `analytics_snapshots` | Aggregated KPI snapshots per period (daily/weekly/monthly/custom). |
| `analytics_reports`   | Tracked report-generation jobs and their lifecycle status.  |

Enums live in `app/constants/analytics.py` and are mirrored as Pydantic
`Literal` types in `app/schemas/analytics.py`:

- `MetricScope`: `volunteer | disaster | public_resource | translation | organization | platform`
- `SnapshotType`: `daily | weekly | monthly | custom`
- `ReportStatus`: `pending | generating | completed | failed`

## KPI Model

Platform overview cards fan out to existing module list endpoints and
render:

- Total volunteers
- Active disasters
- Public resources
- Published translations
- Organizations
- Reports generated

Snapshots persist per-period aggregates in `metrics_json`. Metrics are
aggregated by scope + name across a `recorded_at` window.

## Workflow

### Metrics
`create → update → delete`. Metrics are immutable events; updates are
scoped to `metric_value`, `metric_unit`, and metadata.

### Snapshots
`create → regenerate → delete`. `regenerate` re-runs the aggregation for
the same period and replaces `metrics_json` in place.

### Reports
`pending → generating → (completed | failed) → expired`. Transitions are
guarded by the state machine in `AnalyticsReportService`. Terminal states
allow deletion only.

## RBAC

| Permission           | Grants                                            |
| -------------------- | ------------------------------------------------- |
| `analytics:view`     | List / read metrics, snapshots, reports, KPIs.   |
| `analytics:export`   | Request report jobs; download completed artefacts. |
| `analytics:manage`   | Create / update / delete metrics + snapshots; drive report lifecycle transitions. |

RBAC is enforced by `require_perm(...)` on every mutating endpoint and
by the frontend `usePermissions()` hook (hides unavailable actions).

## API Summary

Base path: `/api/v1/analytics`.

Metrics: `GET /metrics`, `POST /metrics`, `GET /metrics/{id}`,
`PATCH /metrics/{id}`, `DELETE /metrics/{id}`, `GET /metrics/aggregate`.

Snapshots: `GET /snapshots`, `POST /snapshots`, `GET /snapshots/{id}`,
`POST /snapshots/{id}/regenerate`, `DELETE /snapshots/{id}`.

Reports: `GET /reports`, `POST /reports`, `GET /reports/{id}`,
`POST /reports/{id}/start`, `POST /reports/{id}/complete`,
`POST /reports/{id}/fail`, `POST /reports/{id}/expire`,
`DELETE /reports/{id}`.

Legacy overview endpoints (`/overview`, `/time-series`, `/top`, …) remain
in place and unchanged.

## Frontend

Located under `src/routes/_authenticated/analytics.*`:

- `analytics.tsx` — tabbed layout shell.
- `analytics.overview.tsx` — platform KPI dashboard.
- `analytics.metrics.tsx` — searchable, paginated metrics table.
- `analytics.snapshots.tsx` + `analytics.snapshots.$id.tsx` — list, detail,
  regenerate, delete.
- `analytics.jobs.tsx` — report lifecycle management.

Data layer: `src/services/analytics.service.ts` with TanStack Query keys
`analytics`, `analyticsMetrics`, `analyticsSnapshots`, `analyticsReports`,
`analyticsAggregate` (`src/lib/queryKeys.ts`). Types in
`src/types/analytics.ts`.

### Charts

Snapshot detail renders a Recharts bar chart of `metrics_json` values and
a JSON explorer. No custom visualization framework was introduced; the
existing Recharts dependency is reused.

### UX

Every view provides loading skeletons, empty states, error states, status
badges, and confirmation dialogs on destructive actions.

## Integrations

- **Search** — `analytics` scope registered in `app/services/search.py`,
  covering metric names, snapshot metadata, and report names.
- **Audit** — every mutation logs a structured audit event
  (`analytics.metric.*`, `analytics.snapshot.*`, `analytics.report.*`).
- **Notifications** — `analytics_events.py` emits `created / updated /
  deleted / requested / started / completed / failed / expired` events on
  the notification bus.

## Known Limitations

- Report jobs track lifecycle only; no CSV / Excel / PDF file is produced.
- Snapshots must be created and regenerated on demand — no scheduled runs.
- No AI insights, forecasting, or predictive analytics.
- Platform overview KPIs fan out to module list endpoints (N+1 style)
  rather than a materialised roll-up.
- Anonymous / signed report downloads are not exposed.

## Future Work

- **Scheduled jobs** — Celery beat entries to roll snapshots
  daily/weekly/monthly.
- **Report generation** — bind report types to the existing
  `app/services/export.py` renderers; store artefacts via the upload
  pipeline and expose signed download URLs.
- **AI analytics** — plug in the AI gateway for narrative summaries,
  anomaly detection, and forecasting per scope.
- **Per-module dashboards** — drill-downs for volunteer, disaster, public
  information, and translation modules.
