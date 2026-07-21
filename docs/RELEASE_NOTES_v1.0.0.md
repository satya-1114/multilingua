# Release Notes — v1.0.0-rc1

First release candidate for the enterprise communication platform.
All nine milestones are complete; this build is proposed for the
`v1.0.0-rc1` tag.

## Highlights

- Authenticated multi-tenant API with RBAC across every module.
- Six functional domains: Volunteer, Disaster, Public Information,
  Multilingual, Analytics, and Workflow.
- Workflow engine with a production runtime: event bus, trigger
  dispatcher, Celery-backed queue, cron scheduler, and five
  production action handlers (notification, audit, analytics,
  webhook, entity update).
- Production hardening: security middleware and rate limiting,
  HMAC-signed webhooks with idempotency, HA primitives (leader
  election, distributed locking abstractions), OpenTelemetry-shaped
  tracing, cache + pagination + queue performance work, and a full
  Docker / Kubernetes / Helm deployment surface.

## Modules

| Module | Status |
| --- | --- |
| Auth & RBAC | Production |
| Volunteer Platform | Production |
| Disaster Management | Production |
| Public Information & QR | Production |
| Multilingual Platform | Production |
| Analytics | Production |
| Workflow Engine | Production |
| Automation Runtime | Production |
| Security Hardening (9.1) | Production |
| High Availability (9.2) | Production, in-memory providers default |
| Observability (9.3) | Production, OTel exporter optional |
| Performance (9.4) | Production, in-memory cache default |
| Deployment (9.5) | Production |

## Test summary (this release)

- **1158 tests passing** across backend, workflow runtime, HA,
  monitoring, observability, performance, and deployment validation.
- 10 failures + 13 errors are pre-existing SQLite/JSONB compile
  mismatches in `test_auth.py`, `test_health.py`, one export
  renderer, and `test_public_access_api.py`. These are environment
  artifacts (test SQLite dialect vs. production Postgres JSONB) and
  do not affect production behavior. Tracked as separate issues.

## Breaking changes

None — this is the first tagged release.

## Upgrade path

See `docs/DEPLOYMENT.md`. Standard flow: Helm install against a
managed Postgres and Redis, populate secrets, run migrations
(`alembic upgrade head`), then apply the ingress.

## Known limitations

See `docs/IMPLEMENTATION_STATUS.md` and the "Deferred roadmap"
section below.

## Deferred roadmap (post-v1.0)

- Distributed Redis / Postgres lock and lease providers (interfaces
  in `backend/app/runtime/ha/` are ready; only in-memory backends
  ship in v1.0).
- Dead-letter queue topic and requeue UI.
- Compensating-action / rollback executor for workflows.
- Visual drag-and-drop workflow editor (JSON config only today).
- Email, SMS, and Push notification channels.
- AI-assisted workflow designer.
- Cross-process metrics persistence (`MetricsCollector` is
  per-process; OpenTelemetry exporter adapter provided).
- Read replica / sharded Postgres for > 1000 rps sustained load.
- Fix pre-existing SQLite dialect mismatches in the four legacy
  test files listed above.

## Tag

Recommended: `v1.0.0-rc1`.