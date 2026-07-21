# API Integration Guide

Every network call goes through **one HTTP wrapper** (`httpClient`) exposed
through a typed facade (`apiService`) and consumed by module services.
No component calls `fetch` directly.

## Layers

```
component → module service → apiService → httpClient → backend
```

## The `apiService` facade

```ts
import { apiService } from "@/services/api.service";

apiService.get<Foo>("/v1/foo", { params: { page: 1 } });
apiService.post<Foo>("/v1/foo", body);
apiService.put<Foo>("/v1/foo/:id", body);
apiService.patch<Foo>("/v1/foo/:id", body);
apiService.delete<void>("/v1/foo/:id");
```

Options: `params`, `headers`, `signal`, `timeoutMs`, `retryAttempts`,
`deduplicate`. Every method returns the unwrapped `data` from the
`ApiResponse` envelope (`{ data, meta, error }`).

## Response envelope

```ts
interface ApiResponse<T>     { data: T;   meta?: Meta; error?: ApiError; }
interface ApiListResponse<T> { data: T[]; meta: { page, total, … }; error?: ApiError; }
```

Errors are thrown as `ApiError` — services must not swallow them; components
render them through TanStack Query's `error` state.

## Authoring a module service

```ts
// src/services/foo.service.ts
import { apiService } from "@/services/api.service";
import type { Foo, FooCreate, FooListQuery } from "@/types/foo";

export const fooService = {
  list(q: FooListQuery = {}) {
    return apiService.get<Foo[]>("/v1/foos", { params: q });
  },
  get(id: string) {
    return apiService.get<Foo>(`/v1/foos/${id}`);
  },
  create(input: FooCreate) {
    return apiService.post<Foo>("/v1/foos", input);
  },
  update(id: string, patch: Partial<Foo>) {
    return apiService.patch<Foo>(`/v1/foos/${id}`, patch);
  },
  remove(id: string) {
    return apiService.delete<void>(`/v1/foos/${id}`);
  },
};
```

Rules:
1. Types come from `src/types/*`. No `any`.
2. Never re-implement retry, auth, or JSON parsing — `httpClient` owns those.
3. Never store cached lists in module scope — use TanStack Query.
4. Never accept a raw URL from the caller; the service owns the path.

## Consuming a service in a route

```tsx
// src/routes/_authenticated/foos.index.tsx
import { queryOptions, useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { fooService } from "@/services/foo.service";

const foosOptions = queryOptions({
  queryKey: ["foos"],
  queryFn: () => fooService.list(),
});

export const Route = createFileRoute("/_authenticated/foos/")({
  loader: ({ context }) => context.queryClient.ensureQueryData(foosOptions),
  component: FoosPage,
});

function FoosPage() {
  const { data } = useSuspenseQuery(foosOptions);
  return <DataTable rows={data} …/>;
}
```

## Mutations

```tsx
const qc = useQueryClient();
const create = useMutation({
  mutationFn: fooService.create,
  onSuccess: () => qc.invalidateQueries({ queryKey: ["foos"] }),
});
```

## Authentication

- Access token stored via `authService` (memory + `localStorage`).
- `httpClient` attaches `Authorization: Bearer …` automatically.
- On `401`, the client attempts refresh once; on failure it clears the
  session and dispatches a router redirect to `/login`.

## Error handling

Every route with a loader ships:
- `errorComponent` — surfaces the error, offers a retry that calls
  `router.invalidate()`.
- `pendingComponent` (optional) — for expected latency.
- Empty states in the component when the data set is legitimately empty.

## Mock mode

Set `VITE_MOCK_MODE=true` to short-circuit `apiService` to seeded fixtures in
`src/lib/mock/`. All services accept the same call shape — mock and real
implementations are behind the same interface.

## Backend contract references

- `docs/BACKEND-VOLUNTEERS.md`
- `docs/BACKEND-QR.md`
- `docs/BACKEND-DISASTERS.md`
- `docs/BACKEND-MULTILINGUAL.md`
- `docs/BACKEND-ANALYTICS.md`
