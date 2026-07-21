# Component & Module Dependency

## Component tree (high level)

```mermaid
flowchart TD
  Root["__root (html/body shell)"]
  Auth["_authenticated (route gate)"]
  AppLayout["AppLayout (sidebar + topbar + main)"]
  SidebarNav
  TopBar
  Outlet["Route Outlet"]
  RoleGuard
  PermissionGuard

  Root --> Auth --> AppLayout
  AppLayout --> SidebarNav
  AppLayout --> TopBar
  AppLayout --> Outlet
  Outlet --> RoleGuard --> PermissionGuard
```

## Feature modules and their reusable widgets

```mermaid
flowchart LR
  subgraph Common["Shared UI primitives"]
    DataTable
    AnalyticsCard
    StatCard
    DashboardWidget
    EngagementChart
    FormWizard["campaign-wizard"]
    Empty["EmptyState"]
    MPanel["MultilingualPanel"]
    QRPanel["CampaignQRPanel"]
    FilterBar["AnalyticsFilterBar"]
  end

  Campaigns --> DataTable
  Campaigns --> FormWizard
  Campaigns --> QRPanel
  Campaigns --> MPanel
  Disasters --> DataTable
  Disasters --> MPanel
  Volunteers --> DataTable
  Tasks --> DataTable
  Analytics --> AnalyticsCard
  Analytics --> EngagementChart
  Analytics --> FilterBar
  Dashboard --> StatCard
  Dashboard --> DashboardWidget
  Every --> Empty
```

## Module dependency graph

```mermaid
flowchart LR
  RBAC["constants/rbac.ts"]
  RouteAccess["lib/route-access.ts"]
  Api["services/api.service"]
  Http["api/client/http-client"]
  Auth["services/auth.service"]
  Domain["services/{campaign,disaster,volunteer,task,qr,multilingual}.service"]
  Analytics["services/{analytics,report}.service"]

  Http --> Api
  Api --> Domain
  Api --> Analytics
  Auth --> Http
  RouteAccess --> RBAC
  Domain --> RBAC
  Analytics --> Api
```

Rules:
- Components never call `httpClient` directly — always via a service.
- Services never call another service's HTTP wrapper — always via `apiService`.
- Analytics is a single facade; no per-module analytics service.
- Guards, cache keys, and route access rules read from `RBAC` — never re-declare permissions inline.
