/**
 * Enterprise HTTP client with interceptor pipelines, retries, timeouts,
 * cancellation, deduplication and offline queueing. Backwards compatible
 * with the existing api-client surface.
 */

import type { ApiResult, RequestContext, ResponseContext } from "../contracts";
import { environmentService } from "@/services/environment.service";

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface HttpRequestConfig {
  method: HttpMethod;
  path: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
  timeoutMs?: number;
  signal?: AbortSignal;
  retry?: { attempts: number; backoffMs: number };
  deduplicate?: boolean;
  cacheKey?: string;
  context?: RequestContext;
}

export interface PaginationEnvelope {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasMore: boolean;
}

export interface HttpResponseEnvelope<T> {
  data: T;
  status: number;
  headers: Record<string, string>;
  response: ResponseContext;
  pagination?: PaginationEnvelope;
}

export type RequestInterceptor = (config: HttpRequestConfig) => Promise<HttpRequestConfig> | HttpRequestConfig;
export type ResponseInterceptor = <T>(env: HttpResponseEnvelope<T>) => Promise<HttpResponseEnvelope<T>> | HttpResponseEnvelope<T>;
export type ErrorInterceptor = (error: HttpError) => Promise<never | HttpResponseEnvelope<unknown>> | HttpResponseEnvelope<unknown> | never;

export class HttpError extends Error {
  status: number;
  data: unknown;
  code: string;
  constructor(message: string, status: number, code: string, data: unknown) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.code = code;
    this.data = data;
  }
}

const requestInFlight = new Map<string, Promise<unknown>>();

class HttpClient {
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];
  private errorInterceptors: ErrorInterceptor[] = [];
  private offlineQueue: HttpRequestConfig[] = [];

  useRequest(fn: RequestInterceptor) { this.requestInterceptors.push(fn); return this; }
  useResponse(fn: ResponseInterceptor) { this.responseInterceptors.push(fn); return this; }
  useError(fn: ErrorInterceptor) { this.errorInterceptors.push(fn); return this; }

  async request<T>(cfg: HttpRequestConfig): Promise<HttpResponseEnvelope<T>> {
    let finalCfg = { ...cfg };
    for (const it of this.requestInterceptors) finalCfg = await it(finalCfg);

    const key = `${finalCfg.method}:${finalCfg.path}:${JSON.stringify(finalCfg.params ?? {})}`;
    if (finalCfg.deduplicate && requestInFlight.has(key)) {
      return requestInFlight.get(key) as Promise<HttpResponseEnvelope<T>>;
    }

    const run = this.execute<T>(finalCfg);
    if (finalCfg.deduplicate) requestInFlight.set(key, run.finally(() => requestInFlight.delete(key)));
    return run;
  }

  private async execute<T>(cfg: HttpRequestConfig): Promise<HttpResponseEnvelope<T>> {
    if (!environmentService.isOnline()) {
      this.offlineQueue.push(cfg);
      throw new HttpError("Request queued while offline", 0, "OFFLINE", null);
    }

    const attempts = cfg.retry?.attempts ?? 0;
    const backoff = cfg.retry?.backoffMs ?? 200;
    let lastError: HttpError | null = null;

    for (let attempt = 0; attempt <= attempts; attempt++) {
      const start = performance.now();
      try {
        const env = await this.performFetch<T>(cfg);
        env.response.latencyMs = performance.now() - start;
        let out = env;
        for (const it of this.responseInterceptors) out = await it(out);
        return out;
      } catch (err) {
        const httpErr = err instanceof HttpError ? err : new HttpError(String(err), 0, "NETWORK", err);
        lastError = httpErr;
        for (const it of this.errorInterceptors) {
          try { return (await it(httpErr)) as HttpResponseEnvelope<T>; } catch { /* rethrow */ }
        }
        if (attempt < attempts && shouldRetry(httpErr)) {
          await sleep(backoff * Math.pow(2, attempt));
          continue;
        }
        throw httpErr;
      }
    }
    throw lastError ?? new HttpError("Unknown error", 0, "UNKNOWN", null);
  }

  private async performFetch<T>(cfg: HttpRequestConfig): Promise<HttpResponseEnvelope<T>> {
    const base = environmentService.get("API_BASE_URL");
    const url = new URL(cfg.path.startsWith("http") ? cfg.path : `${base}${cfg.path}`,
      typeof window !== "undefined" ? window.location.origin : "http://localhost");
    if (cfg.params) for (const [k, v] of Object.entries(cfg.params)) if (v !== undefined) url.searchParams.set(k, String(v));

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), cfg.timeoutMs ?? 30000);
    cfg.signal?.addEventListener("abort", () => controller.abort());

    try {
      const res = await fetch(url.toString(), {
        method: cfg.method,
        headers: { "Content-Type": "application/json", Accept: "application/json", ...cfg.headers },
        body: cfg.body !== undefined ? JSON.stringify(cfg.body) : undefined,
        signal: controller.signal,
      });
      const ct = res.headers.get("content-type") ?? "";
      const payload = ct.includes("application/json") ? await res.json().catch(() => null) : await res.text();
      if (!res.ok) throw new HttpError(extractErrorMessage(payload, res.statusText), res.status, `HTTP_${res.status}`, payload);
      const headers: Record<string, string> = {};
      res.headers.forEach((v, k) => { headers[k] = v; });
      const apiPayload = payload as {
  success?: boolean;
  data?: unknown;
  pagination?: PaginationEnvelope;
};

return {
  data: (apiPayload.data ?? apiPayload) as T,
  status: res.status,
  headers,
  pagination: apiPayload.pagination,
  response: {
    cached: false,
    fromMock: false,
    latencyMs: 0,
    etag: headers.etag,
  },
};
    } finally {
      clearTimeout(timeout);
    }
  }

  flushOfflineQueue() {
    const queued = [...this.offlineQueue];
    this.offlineQueue = [];
    return Promise.allSettled(queued.map((c) => this.request(c)));
  }

  offlineQueueSize() { return this.offlineQueue.length; }
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object") {
    const p = payload as { error?: unknown; message?: unknown };
    if (p.error && typeof p.error === "object") {
      const nested = (p.error as { message?: unknown }).message;
      if (typeof nested === "string" && nested.length > 0) return nested;
    }
    if (typeof p.message === "string" && p.message.length > 0) return p.message;
  }
  return fallback || "Request failed";
}

function shouldRetry(err: HttpError) {
  return err.status === 0 || err.status === 408 || err.status === 429 || err.status >= 500;
}

function sleep(ms: number) { return new Promise((r) => setTimeout(r, ms)); }

export const httpClient = new HttpClient();

export type ApiClientResult<T> = ApiResult<T>;

// Default interceptors — auth token, correlation id, error mapping.
// The access token is sourced from the single tokenStorage source of truth
// (see src/lib/token-storage.ts). Never read raw localStorage here — it
// diverges from the auth context on refresh/logout and drops in-memory
// tokens.
httpClient.useRequest(async (cfg) => {
  const { tokenStorage } = await import("@/lib/token-storage");
  const token = tokenStorage.getAccessToken();
  const version = environmentService.get("API_VERSION");
  return {
    ...cfg,
    headers: {
      "X-API-Version": version,
      "X-Correlation-Id": cfg.context?.correlationId ?? `cid_${Math.random().toString(36).slice(2, 10)}`,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...cfg.headers,
    },
  };
});

