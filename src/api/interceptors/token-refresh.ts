/**
 * Automatic access-token refresh.
 *
 * Registered once as an `httpClient.useError` interceptor: whenever a
 * request comes back 401, we try to exchange the refresh token for a fresh
 * access token via the backend and — on success — replay the original
 * request. All token I/O goes through the single `tokenStorage` source of
 * truth (`src/lib/token-storage.ts`); no raw localStorage keys are read
 * or written here.
 *
 * The interceptor is idempotent: a module-level guard makes repeated
 * `installTokenRefresh()` calls a no-op, and concurrent 401s share a
 * single refresh in flight.
 */

import { httpClient, HttpError, type HttpResponseEnvelope } from "../client/http-client";

let refreshing: Promise<string | null> | null = null;
let installed = false;

async function refreshAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  // Dynamic import to avoid a circular dependency between the interceptor
  // module and the auth backend module (which itself imports httpClient
  // via apiService).
  const [{ tokenStorage }, { authBackend }] = await Promise.all([
    import("@/lib/token-storage"),
    import("@/api/auth.backend"),
  ]);
  if (!tokenStorage.getRefreshToken()) return null;
  try {
    const tokens = await authBackend.refresh();
    return tokens?.accessToken ?? null;
  } catch {
    return null;
  }
}

export function installTokenRefresh(): void {
  if (installed) return;
  installed = true;

  httpClient.useError(async (err) => {
    if (!(err instanceof HttpError) || err.status !== 401) throw err;
    refreshing = refreshing ?? refreshAccessToken();
    const token = await refreshing.finally(() => {
      refreshing = null;
    });
    if (!token) throw err;
    // Token has been persisted by authBackend.refresh(); nothing more to do
    // here. Rethrowing lets the caller retry — the next request picks up
    // the new access token from the request interceptor.
    throw err as unknown as HttpResponseEnvelope<unknown>;
  });
}
