# Architecture

High-level architecture of the ReachOut (Multilingua) AI-based multilingual
public awareness management platform.

## System diagram

```mermaid
flowchart LR
  subgraph Client["Browser (React 19 + TanStack Start)"]
    UI["UI (shadcn + Tailwind v4)"]
    Router["TanStack Router (file-based routes)"]
    Query["TanStack Query cache"]
    Guards["_authenticated + RoleGuard + PermissionGuard"]
    UI --> Router --> Guards --> Query
  end

  subgraph Edge["TanStack Start server (Vite/Workers-compatible)"]
    ServerFns["createServerFn handlers"]
    Public["/api/public/* routes"]
  end

  subgraph API["FastAPI backend (v1)"]
    Auth["/v1/auth"]
    Domain["/v1/campaigns • /v1/disasters • /v1/volunteers • /v1/tasks"]
    Multi["/v1/multilingual"]
    Analytics["/v1/analytics"]
    Reports["/v1/analytics/exports"]
  end

  subgraph Data["Data plane"]
    PG[("PostgreSQL")]
    MV[("Materialized views")]
    S3[("S3 / object storage")]
    Redis[("Redis cache + queues")]
  end

  Query -->|apiService (fetch + JWT)| Auth
  Query --> Domain
  Query --> Multi
  Query --> Analytics
  Guards -.reads.-> Auth
  Domain --> PG
  Analytics --> MV
  MV -.refresh via pg_cron.-> PG
  Reports --> Redis --> S3
  Public -->|webhooks / cron| Domain
```

## Runtime layers

| Layer            | Responsibility                                                                          |
| ---------------- | --------------------------------------------------------------------------------------- |
| Route            | URL, `validateSearch`, `beforeLoad` (auth/RBAC), `loader` (prime Query cache)           |
| Guard            | `_authenticated` root gate + `RoleGuard` / `PermissionGuard` + `route-access.ts` prefix |
| Service          | `apiService` (typed HTTP facade) → module services → components                         |
| Cache            | TanStack Query keys per resource + filters                                              |
| Presentation     | shadcn primitives (`Card`, `Dialog`, `Table`, `DataTable`) + `AnalyticsCard`, `StatCard`|
| Errors           | Root `errorComponent` + `notFoundComponent`; per-route error components                 |

## Data-flow contract

1. **URL → Route**: TanStack Router matches file-based route.
2. **Route → Auth**: `_authenticated.beforeLoad` reads router context; unauthenticated → `/login`.
3. **Route → RBAC**: `isRouteAllowed(pathname, role)` in `src/lib/route-access.ts` refuses forbidden paths.
4. **Loader → Cache**: `context.queryClient.ensureQueryData(queryOptions)` primes cache.
5. **Component → Data**: `useSuspenseQuery(queryOptions)` subscribes; UI renders.
6. **Mutation → Invalidate**: `useMutation` + `queryClient.invalidateQueries` refresh dependent keys.

## Cross-cutting concerns

- **Auth token**: `authService` stores JWT; `httpClient` attaches `Authorization: Bearer …` and auto-refreshes on 401.
- **Mock toggle**: `VITE_MOCK_MODE=true` short-circuits `apiService` to seeded fixtures (see `src/lib/mock/`).
- **Role model**: 4 roles (Super Admin, Campaign Manager, Volunteer, Viewer) with ~80 permissions. Source of truth: `src/constants/rbac.ts`.
- **Analytics**: Single aggregate endpoint (`/v1/analytics/platform`) — no per-module dashboards.
