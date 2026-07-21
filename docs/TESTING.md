# Testing Recommendations

The project is prepared for a three-tier testing strategy. No tests ship
by default (kept out of the bundle); the sections below describe the
recommended harnesses to add.

## 1. Unit tests — Vitest + Testing Library

Coverage targets: hooks (`use-permissions`, `use-debounced-value`), pure
utilities (`lib/utils`, `route-access.ts`), and service filter
serializers (`serializeAnalyticsFilters`).

### Install
```bash
bun add -d vitest @vitest/ui @testing-library/react @testing-library/jest-dom jsdom
```

### `vitest.config.ts`
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"] },
});
```

### Example — RBAC utility
```ts
import { describe, expect, it } from "vitest";
import { isRouteAllowed } from "@/lib/route-access";
import { ROLES } from "@/constants/rbac";

describe("route-access", () => {
  it("denies Viewer on /analytics", () => {
    expect(isRouteAllowed("/analytics/platform", ROLES.VIEWER)).toBe(false);
  });
  it("allows Volunteer on /analytics/platform", () => {
    expect(isRouteAllowed("/analytics/platform", ROLES.VOLUNTEER)).toBe(true);
  });
});
```

## 2. Integration tests — Vitest + Testing Library + MSW

Coverage targets: route rendering with a stubbed API, form submissions,
mutation → invalidation cycles.

### Install
```bash
bun add -d msw
```

### Approach
- Mount routes with a real `QueryClient` + memory router.
- Use `msw` to stub `/v1/*` endpoints deterministically.
- Assert on rendered DOM and cache mutations.

### Example scaffolding
```ts
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const server = setupServer(
  http.get("/v1/campaigns", () => HttpResponse.json({ data: [], meta: { total: 0 } })),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## 3. End-to-end — Playwright

Coverage targets: sign-in flow per role, campaign create-to-publish,
volunteer task acceptance, QR public landing page, analytics filter +
export.

### Install
```bash
bun add -d @playwright/test
bunx playwright install chromium
```

### `playwright.config.ts`
```ts
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080" },
  webServer: { command: "bun dev", url: "http://localhost:8080", reuseExistingServer: true },
});
```

### Suggested test matrix

| Suite               | Roles                          | Notes                                      |
| ------------------- | ------------------------------ | ------------------------------------------ |
| Auth                | all                            | login, register (dynamic fields), logout   |
| RBAC gates          | Viewer, Volunteer, Manager     | manual URL entry to protected routes       |
| Campaigns           | Manager                        | wizard → publish → QR generate             |
| Public campaign     | anonymous                      | scan URL renders, language persists        |
| Disasters           | Manager                        | create → assign volunteer → close          |
| Analytics           | Admin, Manager, Volunteer      | scope + filters + CSV export               |

## CI recommendation

```yaml
jobs:
  test:
    steps:
      - bun install --frozen-lockfile
      - bunx tsgo --noEmit
      - bunx eslint src
      - bunx vitest run --coverage
  e2e:
    needs: test
    steps:
      - bunx playwright test
```

Fail the pipeline on any of: typecheck errors, lint errors, unit-test
failures, coverage regression >2%, e2e failures.
