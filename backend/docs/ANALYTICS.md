# Analytics & Reporting Engine

## Overview

The analytics service (`app/services/analytics.py`) provides workspace-scoped
aggregations, time-series bucketing, and cross-domain KPIs. Results are
cached in Redis (in-process fallback) with short TTLs.

## Domains

- `campaigns`, `audience`, `deliveries`, `ai`, `notifications`, `audit`

## Endpoints

- `GET /api/v1/analytics/overview` — headline KPIs
- `GET /api/v1/analytics/time-series` — bucketed counts + moving average + growth
- `GET /api/v1/analytics/top` — top/bottom performers
- `GET /api/v1/analytics/{campaigns,audience,communication,ai,security,notifications}`
- `GET /api/v1/analytics/benchmarks` — workspace vs platform average
- `GET /api/v1/analytics/dashboard` — role-based widget snapshot

## Reports

`app/services/reports.py` binds report kinds to analytics queries and hands the
result to `app/services/export.py` for CSV / Excel / JSON / PDF rendering.

- `POST /api/v1/reports` — create scheduled/one-off report definitions
- `POST /api/v1/reports/{id}/run?format=csv|excel|pdf|json` — execute
- `POST /api/v1/reports/ad-hoc?kind=...&format=...` — run without saving

## Global Search

- `GET /api/v1/search?q=...&scopes=campaign,audience,template`
- `GET /api/v1/search/suggest?q=...`

Search is permission-aware: scopes are silently dropped when the caller lacks
the associated `*:view` permission.

## Upload pipeline

- `POST /api/v1/media` — single-shot upload with optional image optimisation
- `POST /api/v1/media/chunks/init` → `POST /media/chunks/{sid}` → `POST /media/chunks/{sid}/complete`
- `GET  /api/v1/media/{id}/signed-url` — HMAC-signed download URL

## Notifications

Delivery, digest, mark-read/unread, and preferences with quiet-hours
enforcement live under `/api/v1/notifications`.

## Monitoring

- `GET /api/v1/monitoring/health`
- `GET /api/v1/monitoring/system` — CPU / memory / disk
- `GET /api/v1/monitoring/database` — pg_stat snapshot
- `GET /api/v1/monitoring/queues` — Celery inspect
- `GET /api/v1/monitoring/metrics` — Prometheus text exposition

## Frontend adapter

Import from `src/api/backend.ts`:

```ts
import { backendApi } from "@/api/backend";

const overview = await backendApi.analytics.overview(workspaceId);
const hits = await backendApi.search.search({ q: "onboarding" });
```
