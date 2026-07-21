/**
 * Facade over the HTTP client, providing typed helpers services use
 * throughout the app.
 */

import { httpClient } from "@/api/client/http-client";
import type { HttpMethod } from "@/api/client/http-client";
import type { ApiListResponse, ApiResponse } from "@/api/contracts";
import { environmentService } from "./environment.service";

interface Options {
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeoutMs?: number;
  retryAttempts?: number;
  deduplicate?: boolean;
}

async function call<T>(method: HttpMethod, path: string, body?: unknown, opts: Options = {}): Promise<T> {
  const env = await httpClient.request<T>({
    method,
    path,
    body,
    params: opts.params,
    headers: opts.headers,
    signal: opts.signal,
    timeoutMs: opts.timeoutMs,
    retry: opts.retryAttempts ? { attempts: opts.retryAttempts, backoffMs: 250 } : undefined,
    deduplicate: opts.deduplicate,
  });
  return env.data;
}

export const apiService = {
  get<T>(path: string, opts?: Options) { return call<T>("GET", path, undefined, opts); },
  post<T>(path: string, body?: unknown, opts?: Options) { return call<T>("POST", path, body, opts); },
  put<T>(path: string, body?: unknown, opts?: Options) { return call<T>("PUT", path, body, opts); },
  patch<T>(path: string, body?: unknown, opts?: Options) { return call<T>("PATCH", path, body, opts); },
  delete<T>(path: string, opts?: Options) { return call<T>("DELETE", path, undefined, opts); },
  isMock: () => environmentService.isMock(),
  health: async () => ({ ok: true, mock: environmentService.isMock(), env: environmentService.get("ENVIRONMENT") }),
};

export type { ApiResponse, ApiListResponse };
