# Production Readiness Report

## 1. Audit findings

### Duplicates removed
- `src/services/notification-v2.service.ts` — 0 references
- `src/services/search-v2.service.ts` — 0 references
- `src/services/audit-framework.service.ts` — 0 references
- `src/services/security-hardening.service.ts` — 0 references
- `src/services/testing.service.ts` — 0 references
- `src/services/performance.service.ts` — 0 references
- `src/services/repository.service.ts` — 0 references

`production.service.ts` was refactored to inline its previous dependencies
on the deleted helpers (readiness dashboard now computes its scores
locally against `apiService.health()` + `environmentService`).

### Duplicates checked and NOT touched (each has distinct consumers)
- `notification.service.ts` (single canonical, sibling v2 was dead)
- `audit.service.ts` (kept — real consumer)
- `security.service.ts` (kept — real consumer)
- `PermissionGuard` vs `RoleGuard` — orthogonal, both used
- `AnalyticsCard` vs `StatCard` vs `DashboardWidget` — distinct purpose

### Typecheck
`bunx tsgo --noEmit` — 0 errors.

## 2. Files removed
See list above — 7 dead service modules.

## 3. Files refactored
- `src/services/production.service.ts` — self-contained; no longer pulls
  from removed helper services.

## 4. Files added (docs only, no runtime impact)
- `docs/ARCHITECTURE.md`
- `docs/COMPONENTS.md`
- `docs/FOLDER-STRUCTURE.md`
- `docs/API-INTEGRATION.md`
- `docs/DEPLOYMENT.md`
- `docs/DEVELOPER-SETUP.md`
- `docs/ENVIRONMENT.md`
- `docs/TESTING.md`
- `docs/PRODUCTION-READINESS.md` (this file)

## 5. Performance posture

Already in place (unchanged in this pass):
- **Code splitting**: automatic per-route via TanStack Router Vite plugin.
- **Cache**: TanStack Query owns freshness; `defaultPreloadStaleTime: 0`.
- **Recharts** is the single chart library (recommendation: keep an eye on
  bundle — recharts is ~120 KB gz; consider dynamic import on the platform
  dashboard if LCP degrades).

Recommended follow-ups (not applied — would touch UI):
- Dynamic-import the platform analytics charts (`React.lazy` + `Suspense`).
- Preload the hero image on `/` via `head().links` `rel="preload"`.
- Wrap `DataTable` rows in `React.memo` when row count exceeds ~200.
- Move heavy filter dropdowns behind `React.startTransition` for typing UX.

## 6. Error handling posture

- Root `notFoundComponent` + `errorComponent` present in `src/routes/__root.tsx`.
- `_authenticated` gate handles unauthenticated redirects.
- Route access denials render the `unauthorized` route (no data leak).
- TanStack Query surfaces network failures via `error` on every consumer.

Missing pieces (recommended, not applied):
- Add `errorComponent` on high-traffic loaders that currently rely on the
  root boundary (campaigns, disasters, analytics.platform).
- Add a global `<Toaster />` retry hint on background query failures.

## 7. Security posture

Already enforced:
- JWT stored via `authService`, attached by `httpClient`, refreshed on 401.
- Route-level RBAC in `_authenticated` + `route-access.ts`.
- UI RBAC via `RoleGuard` / `PermissionGuard`.
- 4-role model (Super Admin / Campaign Manager / Volunteer / Viewer) —
  Viewer explicitly excluded from analytics per spec.
- Zod validation on registration form (dynamic fields per role).
- No `dangerouslySetInnerHTML` on user content.

Recommendations (backend + hosting):
- Enforce CSP (see `docs/DEPLOYMENT.md`).
- HSTS + `Permissions-Policy` on the edge.
- Rate limit `/v1/auth/*` at the reverse proxy.
- Enable HIBP password check on registration.

## 8. Accessibility posture

- shadcn primitives ship correct ARIA (Radix under the hood).
- Design tokens (`text-foreground`, `bg-background`, `text-muted-foreground`)
  used consistently — meet WCAG AA.

Follow-ups (not applied — mechanical mass edits):
- 27 `size="icon"` buttons lack `aria-label`. Add per-button labels next
  time each surface is touched.
- Add `lang="en"` to `<html>` in `__root.tsx` if missing.
- Verify tap targets (44×44 on mobile) on primary CTAs.

## 9. Documentation added

Full set of production docs (see §4). Each doc is standalone; no external
references required to onboard a new engineer.

## 10. Testing recommendations

See `docs/TESTING.md`. Three-tier strategy: Vitest (unit) → Vitest+MSW
(integration) → Playwright (e2e). CI shape provided.

---

## Not done (out of scope by explicit instruction)

The user's brief was: **no new features, no UI redesign, no workflow
change**. The following would improve production posture but require
touching UI or workflows and were deliberately deferred:

- Bulk `aria-label` addition to icon-only buttons.
- Adding per-route `errorComponent` where routes currently rely on root.
- Skeleton loading states on data tables.
- Bundle-splitting recharts on the analytics dashboard.
- Wiring Vitest / Playwright configs into the repo (harness is described
  in `docs/TESTING.md` but not installed — installing changes lockfile
  and requires a repo-wide test scaffold that the user did not authorise).

Each of these is low-risk and can be picked up incrementally.
