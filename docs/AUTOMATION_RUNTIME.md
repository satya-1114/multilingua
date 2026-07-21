# Automation Runtime (Milestone 8)

Production-ready execution layer for the Workflow Engine. Turns stored
`WorkflowDefinition` rows into observable, retryable, event- and schedule-driven
executions with a pluggable action registry.

## Architecture Overview

```
                    ┌──────────────────────┐
  Application ─────►│  Event Bus (Phase 2) │
  events            └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Trigger Dispatcher   │  filter: conditions_json
                    └──────────┬───────────┘
                               │
  Scheduler ──cron──►┌─────────▼──────────┐
  (Phase 3)          │ WorkflowQueue      │  Celery | InMemory
                     └─────────┬──────────┘
                               │
                    ┌──────────▼───────────┐
                    │ RuntimeExecutor      │  walks actions in order
                    │  + Context           │  records step results
                    │  + ActionRegistry    │
                    └──────────┬───────────┘
                               │
     ┌─────────────┬───────────┼──────────┬─────────────┐
     ▼             ▼           ▼          ▼             ▼
 Notification   Audit    Analytics    Webhook     UpdateEntity
   handler    handler     handler     handler       handler
     └─────────────┴───────────┼──────────┴─────────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Monitoring (Phase 5) │  metrics / health /
                    └──────────────────────┘  statistics / retries
```

## Package Layout (`backend/app/runtime/`)

| Path | Purpose |
| ---- | ------- |
| `executor.py` | `WorkflowRuntimeExecutor` — sequential walker over enabled actions. |
| `registry.py` | `ActionRegistry` + `BaseActionHandler` contract. |
| `context.py` | `WorkflowExecutionContext` (immutable per run: ids, payload, db, logger, dry_run). |
| `result.py` | `ActionResult`, `ExecutionResult` value objects. |
| `exceptions.py` | Runtime exception hierarchy (`RuntimeError`, `HandlerError`, `ValidationError`, `RetryableError`). |
| `base.py` | `BaseActionHandler` abstract class. |
| `service.py` | `WorkflowRuntimeService` — public facade (`enqueue_execution`, `run_execution`). |
| `action_handlers/` | Production handlers: `notification`, `audit`, `analytics`, `webhook`, `update_entity`, plus `_base.ProductionActionHandler`. |
| `events/` | `WorkflowEventBus`, `WorkflowEvent`, `WorkflowTriggerDispatcher`, filter engine, publishers, subscribers. |
| `scheduler/` | `WorkflowScheduler` (crontab), `WorkflowQueue` (Celery / InMemory), `celery_app.py`, `tasks.py`, `worker.py`. |
| `monitoring/` | `MetricsCollector`, `ExecutionRetryHistoryService`, `WorkflowRuntimeHealth`, `WorkflowStatisticsService`. |

## Event Flow

1. **Publish** — Application modules (`app.services.volunteer`,
   `app.services.disaster`, `app.services.analytics`, …) call
   `runtime.events.publisher.publish_event(WorkflowEvent(...))` after their own
   commit. The bus is synchronous and in-process; failures are isolated so they
   never roll back the caller.
2. **Match** — `WorkflowTriggerDispatcher` queries `WorkflowTrigger` rows
   whose `trigger_type == "event"` and event name matches. It applies the
   filter engine to `conditions_json` (operators: `eq`, `ne`, `in`, `contains`,
   `gt`, `lt`, `and`, `or`).
3. **Enqueue** — For each matching trigger, the dispatcher calls
   `WorkflowRuntimeService.enqueue_execution(definition_id, payload, dry_run)`.
4. **Execute** — `WorkflowQueue.enqueue(...)` hands off to Celery in
   production or runs inline for tests/dev.
5. **Record** — Executor walks enabled actions in `sequence_order`, records a
   `WorkflowExecutionStep` per action, and updates the parent
   `WorkflowExecution` status.

## Scheduler

- Uses Celery `crontab` semantics for cron validation and next-run computation.
- Each `WorkflowTrigger.trigger_type == "schedule"` is registered with the
  scheduler; the beat loop enqueues via `WorkflowQueue`.
- Naive datetimes are treated as UTC.

## Queue Abstraction

`WorkflowQueue` is a thin protocol with two implementations:

| Implementation | Purpose |
| -------------- | ------- |
| `CeleryWorkflowQueue` | Production. Delegates to `execute_workflow_task` (isolated `workflow_celery_app`, exponential backoff + jitter). |
| `InMemoryWorkflowQueue` | Tests and dev. Runs synchronously in-process. |

Only `service.py` and `scheduler/` know which backend is active; the executor
and handlers are queue-agnostic.

## Celery Integration

- Dedicated `workflow_celery_app` (separate from any future project-wide
  Celery). Isolated queues (`workflow.default`, `workflow.high`,
  `workflow.low`).
- `execute_workflow_task` retries with exponential backoff and jitter; hard
  ceiling on retry count comes from the definition.
- Broker/backend configured via env. Absent broker → health probe returns
  `unknown` (best-effort; does not degrade overall status).

## Action Handlers

All handlers inherit from `ProductionActionHandler`, which adds structured
logging, execution timing, and the `dry_run` safety valve. Each handler
consumes services only — never repositories or ORM directly.

| Handler | Config keys (excerpt) | Effect |
| ------- | --------------------- | ------ |
| `notification` | `recipients` (user_ids / role / broadcast), `title`, `body`, `channel` | `NotificationService.dispatch(...)`. |
| `audit` | `action`, `entity_type`, `entity_id`, `metadata` | `AuditService.record(...)`. |
| `analytics` | `metric`, `value`, `dimensions` | `AnalyticsService.record_metric(...)`. |
| `webhook` | `url`, `method`, `headers`, `body_template`, `timeout_s` | Outbound `httpx` request; response captured on step. |
| `update_entity` | `entity` (`volunteer` / `disaster` / `public_resource`), `id`, `changes` | Delegates to the owning service. |

## Monitoring (Phase 8.5)

- **Metrics** — In-memory `MetricsCollector` (`default_metrics`) records
  execution counts by status and workflow, duration (count/total/avg/min/max),
  per-handler duration, queue latency, retries, and action success/failure.
  Executor emits at completion of each execution and action.
- **Health** — `WorkflowRuntimeHealth` probes registry (required handlers
  present), scheduler importability, queue backend connectivity, Celery broker
  (best-effort), and handler instantiability. Aggregate status is
  worst-of-checks; Celery `unknown` never degrades overall.
- **Statistics** — `WorkflowStatisticsService` runs aggregate queries over
  `WorkflowExecution` and `WorkflowExecutionStep` (success rate, avg duration,
  top workflows, top failing workflows) with a `since` window.
- **Retry history** — `ExecutionRetryHistoryService` reads per-step retry
  attempts and error messages.

## API Summary

All endpoints require `workflow:manage`. Standard `ok()` / `paginated()`
envelopes; camelCase payloads.

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/runtime/health` | Overall + per-sub-check status. |
| GET | `/runtime/metrics` | Snapshot of the in-memory collector. |
| GET | `/runtime/statistics?since=&topLimit=` | Aggregate KPIs from DB. |
| GET | `/runtime/executions/{id}/retries` | Retry attempts for one execution. |

Existing `/workflows/*` router (Phase 7.3) is unchanged; RBAC unchanged.

## Operational Dashboard (Frontend)

`src/routes/_authenticated/workflows.index.tsx` renders:

- KPI cards: **Success Rate**, **Retries**, **Avg Runtime**, **Health**.
- Runtime health panel: per-sub-check status list.
- Existing definition / execution / recent-failures widgets from Phase 7.5.

Data flows through `workflowEngineService.runtime{Health,Statistics}` and
`retryHistory`; query keys live in `src/lib/queryKeys.ts`. All runtime UI is
gated on `workflow:manage`.

## Known Limitations

- **Rollback placeholders** — Action results carry `rollback_hint` fields,
  but no compensating-action executor exists yet.
- **Webhook idempotency** — Outbound webhook handler does not attach an
  `Idempotency-Key` header; receivers must dedupe on their side.
- **Distributed scheduling** — `WorkflowScheduler` assumes a single beat
  process. No leader election / lock table yet.
- **OpenTelemetry** — Structured logs only; no OTEL spans or exporters.
- **Dead-letter queue** — Exhausted retries mark the execution `failed`
  in Postgres; there is no separate DLQ topic or UI to requeue.
- **Metrics persistence** — `MetricsCollector` is per-process and resets on
  restart. Long-range trends must query `WorkflowExecution`.
- **Tracing** — No end-to-end trace correlation across event → dispatcher
  → queue → executor → handler (log fields carry ids, but no span context).

## Future Enhancements

- Compensating-action / saga executor over rollback hints.
- OTEL tracing + Prom/StatsD exporter for `MetricsCollector`.
- DLQ topic and requeue endpoint / UI.
- Distributed scheduler with lease-based leader election.
- Webhook idempotency headers and signed payloads.
- JSON-schema-driven handler config validation surfaced in the definition editor.
- Visual workflow editor (currently JSON only).

## Test Coverage

- `test_workflow_runtime.py` — 40 tests (executor / registry / context / results).
- `test_workflow_runtime_production.py` — 89 tests (production handlers).
- `test_workflow_events_bus.py` — 50 tests (bus + dispatcher + filters).
- `test_workflow_scheduler.py` — 88 tests (queue + scheduler + Celery task).
- `test_workflow_monitoring.py` — 76 tests (metrics / health / statistics / retries / API).
- Plus 105 pre-existing workflow tests (Phase 7).

Total: **448 workflow-scoped tests, all passing.**
