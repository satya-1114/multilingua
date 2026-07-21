# Workflow Engine Module

_Phase 7 (7.1 – 7.6). Automation & Workflow Engine — data model, services, API,
integration facade, and management UI._

## Architecture

The Workflow Engine follows the same layered pattern used across the platform:

```
Router (thin)  →  Service (business logic)  →  Repository (thin ORM)  →  Model
                          │
                          ▼
              Integration facade (isolated side-effects:
              audit · notifications · search · analytics)
```

- **Router** (`backend/app/api/v1/workflow.py`) – HTTP transport, DI, serialisation.
- **Service** (`backend/app/services/workflow.py`) – all validation, state-machine
  transitions, ordering, RBAC-domain rules.
- **Repository** (`backend/app/repositories/workflow.py`) – pure query helpers.
- **Model** (`backend/app/models/workflow.py`) – SQLAlchemy 2 declarative.
- **Schemas** (`backend/app/schemas/workflow.py`) – Pydantic DTOs.
- **Integration facade** (`backend/app/integrations/workflow_events.py`) –
  the only place that reaches into audit / notifications / search / analytics.
  Every call is wrapped in failure-isolation so integration errors never
  break workflow mutations.

## Domain Model

### WorkflowDefinition
The reusable automation blueprint owned by an organisation.

| Field         | Notes                                                       |
| ------------- | ----------------------------------------------------------- |
| `id`          | UUID PK                                                     |
| `org_id`      | Tenant scope                                                |
| `name`        | Human label                                                 |
| `description` | Optional                                                    |
| `is_enabled`  | Only enabled definitions may start executions               |
| `metadata`    | JSON free-form                                              |
| `created_by`  | User FK                                                     |
| `created_at` / `updated_at` | Standard timestamps                           |

### WorkflowTrigger
Declares *when* a workflow should run. Multiple triggers per definition.

- `trigger_type` ∈ `manual`, `event`, `schedule`, `webhook`, `condition`.
- `config` — trigger-specific JSON (event name, cron, webhook secret, etc.).
- `is_enabled` — disabled triggers are ignored by future dispatchers.

### WorkflowAction
An ordered step inside a workflow.

- `action_type` — free-form string identifying an executor handler
  (`notify`, `http_request`, `assign`, …).
- `sequence` — 0-indexed execution order. Reordering is atomic in the service
  layer.
- `config` — action-specific JSON payload.
- `is_enabled` — disabled actions are skipped during execution.

### WorkflowExecution
A single run of a `WorkflowDefinition`.

- `status` state machine (see below).
- `trigger_id` (nullable) — which trigger fired the run, if any.
- `input` / `output` / `error` — JSON.
- `started_at` / `finished_at` — populated on transition.

### WorkflowExecutionStep
A per-action record produced during an execution.

- `status` state machine (see below).
- `attempts` — incremented on retry.
- `input` / `output` / `error` — JSON.

## Execution Lifecycle

```
pending ──▶ running ──▶ succeeded
                │
                ├──▶ failed
                └──▶ cancelled
```

- `pending → running` on start; sets `started_at`.
- `running → succeeded | failed | cancelled` are terminal; sets `finished_at`.
- Terminal executions cannot be mutated (guarded in the service layer).

## Execution Step Lifecycle

```
pending ──▶ running ──▶ succeeded
                │
                ├──▶ failed  ──(retry)──▶ pending
                └──▶ skipped
```

- `retry` on a failed step resets it to `pending`, increments `attempts`,
  clears `error`, and keeps the parent execution alive.

## RBAC

Backend permissions (see `backend/app/security/rbac.py`):

| Permission          | Grants                                              |
| ------------------- | --------------------------------------------------- |
| `workflow:view`     | Read definitions, triggers, actions, executions.    |
| `workflow:create`   | Create definitions, triggers, actions.              |
| `workflow:update`   | Update / reorder / enable / disable / delete.       |
| `workflow:execute`  | Start executions, transition status, retry steps.   |
| `workflow:manage`   | Legacy umbrella — implied by the granular set.      |

Frontend mirror (`src/constants/rbac.ts`) exposes the same permissions and
gates UI affordances in every workflow route.

## API Summary

Mounted under `/v1/workflows` (17 unique paths, 33 handlers).

| Group        | Endpoints                                                                 |
| ------------ | ------------------------------------------------------------------------- |
| Definitions  | `GET/POST /` · `GET/PATCH/DELETE /{id}` · `POST /{id}/enable` · `/disable`|
| Triggers     | `GET/POST /{id}/triggers` · `GET/PATCH/DELETE /triggers/{triggerId}`      |
| Actions      | `GET/POST /{id}/actions` · `GET/PATCH/DELETE /actions/{actionId}` · `POST /{id}/actions/reorder` |
| Executions   | `GET /executions` · `GET /{id}/executions` · `POST /{id}/executions` · `GET /executions/{executionId}` · `POST /executions/{executionId}/{complete\|fail\|cancel}` |
| Steps        | `GET /executions/{executionId}/steps` · `POST /steps/{stepId}/{transition\|retry}` |

All responses use the platform `ok()` / `paginated()` camelCase envelopes.

## Frontend Overview

Routes live under `src/routes/_authenticated/workflows*`:

| Route                              | Page                                    |
| ---------------------------------- | --------------------------------------- |
| `/workflows`                       | Dashboard (KPIs + recent activity)      |
| `/workflows/definitions`           | Definitions list · CRUD · enable/disable |
| `/workflows/$id`                   | Detail: Actions · Triggers · Executions |
| `/workflows/executions`            | Global execution history                |
| `/workflows/executions/$id`        | Execution detail + step timeline        |

Supporting modules:

- `src/types/workflow.ts` — DTOs mirroring backend schemas.
- `src/services/workflow-engine.service.ts` — thin REST facade + dashboard
  aggregator (kept separate from the legacy campaign-FSM `workflow.service.ts`).
- `src/components/workflows/workflow-status-badge.tsx` — shared status badge.
- `src/lib/queryKeys.ts` — `workflow`, `workflowDefinitions`, `workflowTriggers`,
  `workflowActions`, `workflowExecutions`, `workflowSteps` key factories.

Every page renders skeleton loaders, empty states, and inline
access-denied alerts for RBAC-blocked users; every mutation invalidates
only the affected query keys and reports via `sonner` toasts.

## Integrations

All side-effects are funnelled through
`backend/app/integrations/workflow_events.py`. Individual integration
failures are caught and logged; they never bubble into the caller.

### Audit events
- `workflow.definition.{created,updated,enabled,disabled,deleted}`
- `workflow.trigger.{created,updated,deleted}`
- `workflow.action.{created,updated,reordered,deleted}`
- `workflow.execution.{started,succeeded,failed,cancelled}`
- `workflow.step.{transitioned,retried}`

### Notification events
- Emitted on `execution.failed` with high priority to workflow owners and
  organisation admins.
- Emitted on `definition.disabled` (informational) to organisation admins.

### Search scope
- Registered scope: `workflow` — indexes `WorkflowDefinition` name,
  description, and `metadata` free-text.

### Analytics events
- The facade emits `workflow.execution.*` counters into the analytics
  metric bus; scheduled snapshotting is left to the analytics platform.

## Known Limitations

- **No runtime executor.** The engine persists the *definition* of
  automation; there is no dispatcher, no Celery worker, and no scheduler
  wired yet. Triggers and executions are managed by API callers.
- **Manual triggers only in practice.** `event`, `schedule`, `webhook`,
  and `condition` triggers are storable but nothing consumes them.
- **No visual editor.** Actions are edited as JSON config; a drag-and-drop
  or graph-based editor is not in scope for Phase 7.
- **No backend-side action library.** `action_type` is a free-form string;
  a registry / validation of executor handlers is deferred.
- **Frontend reorder uses up/down buttons**, not drag-and-drop, pending an
  approved `@dnd-kit` dependency.
- **No frontend test infrastructure** exists in the repo (no Vitest / RTL
  configured). Verification relies on the backend suite (104 tests) and
  the strict `tsgo` typecheck.

## Roadmap

- **Scheduler** — cron-driven trigger evaluator (Celery beat) that
  materialises executions from `schedule` triggers.
- **Celery workers** — an executor pool that consumes `pending` executions,
  drives step transitions, and handles retries with backoff.
- **Event dispatcher** — subscribe workflow `event` triggers to the
  platform notification / audit bus so lifecycle events on other modules
  can start workflows.
- **Webhook ingress** — public `/api/public/workflows/webhook/{token}`
  endpoint that verifies signatures and enqueues executions.
- **Visual workflow editor** — graph UI backed by the same
  definitions/triggers/actions API.
- **Action registry** — typed handler catalog with JSON-schema config
  validation.
- **AI builder** — natural-language → workflow definition.
