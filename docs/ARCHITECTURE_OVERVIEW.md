# Architecture Overview

A single-page reference for the platform as of v1.0.0-rc1. Each
section links to the module-level document that owns the details.

## Shape

```
                ┌───────────────────────────────────────┐
   users ─────▶ │  TanStack Start frontend (Nginx)      │
                └───────────────┬───────────────────────┘
                                │  HTTPS / JSON
                ┌───────────────▼───────────────────────┐
                │  FastAPI backend (gunicorn+uvicorn)   │
                │  ├─ Auth & RBAC                       │
                │  ├─ Domain modules (6)                │
                │  ├─ Workflow engine + runtime         │
                │  ├─ Security middleware               │
                │  ├─ Observability (correlation, spans)│
                │  └─ Cache + pagination                │
                └──┬────────────────────────┬───────────┘
                   │                        │
          ┌────────▼─────┐          ┌───────▼────────┐
          │  PostgreSQL  │          │  Redis         │
          │  (durable)   │          │  (broker + HA) │
          └──────────────┘          └───────┬────────┘
                                            │
                          ┌─────────────────▼──────────────┐
                          │  Celery worker(s)              │
                          │  Celery beat scheduler (1x)    │
                          └────────────────────────────────┘
```

## Layered organization

| Layer | Location | Purpose |
| --- | --- | --- |
| API | `backend/app/api/v1/` | HTTP handlers, response envelopes, RBAC guards |
| Services | `backend/app/services/` | Business rules, transitions, validation |
| Repositories | `backend/app/repositories/` | Data access on top of `CRUDBase` |
| Runtime | `backend/app/runtime/` | Executor, event bus, scheduler, HA, handlers |
| Integrations | `backend/app/integrations/` | Cross-module side-effects (audit, notify, search, analytics) |
| Security | `backend/app/security/`, `backend/app/middleware/` | Headers, rate limit, webhooks, file validation |
| Observability | `backend/app/observability/` | Correlation, tracing, metrics |
| Cache | `backend/app/cache/` | Pluggable cache + pagination helpers |

## Data flow (workflow execution)

1. A domain module calls `publish_event()` on the event bus.
2. `WorkflowTriggerDispatcher` matches the event against stored
   triggers (filter engine on `conditions_json`).
3. Matched executions are enqueued via `WorkflowQueue`
   (`ResilientWorkflowQueue` → `CeleryWorkflowQueue`).
4. A Celery worker runs `execute_workflow_task`, which calls
   `WorkflowRuntimeExecutor.execute()`.
5. The executor walks enabled actions, invoking each production
   handler inside an `observed()` span with correlation context.
6. State transitions flow through `WorkflowExecutionService`; audit,
   notification, and analytics side-effects are best-effort.

## Cross-cutting concerns

- **RBAC**: enforced per endpoint via permission strings; every
  module owns its permission set.
- **Audit**: every state transition and privileged action.
- **Search**: eight registered scopes.
- **Idempotency**: at execution (Phase 9.2) and webhook levels.
- **Rate limiting**: IP / user / endpoint tiers.
- **HA**: leader election gates the scheduler; queue is resilient
  with exponential backoff.

## Deployment

- Containers: `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`.
- Kubernetes: `deploy/k8s/` raw manifests, or `deploy/helm/` chart.
- Probes: `/health`, `/health/live`, `/health/ready`, `/healthz`.
- CI/CD: four GitHub Actions workflows.

See `docs/DEPLOYMENT.md`, `docs/RUNBOOK.md`, `docs/PERFORMANCE.md`,
`docs/BACKUP_AND_RECOVERY.md`, `docs/WORKFLOW_MODULE.md`, and
`docs/AUTOMATION_RUNTIME.md` for module-level detail.