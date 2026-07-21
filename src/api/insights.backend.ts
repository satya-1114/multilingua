/**
 * Real-backend adapters for Slice 4 modules: analytics, reports, global
 * search, media/upload pipeline, and notifications.
 *
 * All calls go through `apiService`. Enable by setting
 * `VITE_MOCK_MODE=false` and `VITE_API_BASE_URL=...`.
 */

import { apiService } from "@/services/api.service";

export type Granularity = "day" | "week" | "month" | "quarter" | "year";

export interface TimeSeriesPoint {
  bucket: string;
  value: number;
}

export interface TimeSeriesResponse {
  series: TimeSeriesPoint[];
  movingAverage: number[];
  total: number;
  previousTotal: number;
  growthPct: number;
  granularity: Granularity;
  start: string;
  end: string;
}

export const analyticsApi = {
  overview: (workspaceId?: string) =>
    apiService.get("/analytics/overview", { params: { workspace_id: workspaceId } }),
  timeSeries: (params: {
    domain: string;
    granularity?: Granularity;
    start?: string;
    end?: string;
    workspaceId?: string;
  }) =>
    apiService.get<TimeSeriesResponse>("/analytics/time-series", {
      params: {
        domain: params.domain,
        granularity: params.granularity ?? "day",
        start: params.start,
        end: params.end,
        workspace_id: params.workspaceId,
      },
    }),
  top: (params: { kind?: "campaigns" | "templates" | "workspaces"; limit?: number; workspaceId?: string; ascending?: boolean }) =>
    apiService.get("/analytics/top", {
      params: {
        kind: params.kind ?? "campaigns",
        limit: params.limit ?? 10,
        workspace_id: params.workspaceId,
        ascending: params.ascending,
      },
    }),
  campaigns: (workspaceId?: string) => apiService.get("/analytics/campaigns", { params: { workspace_id: workspaceId } }),
  audience: (workspaceId?: string) => apiService.get("/analytics/audience", { params: { workspace_id: workspaceId } }),
  communication: (workspaceId?: string) => apiService.get("/analytics/communication", { params: { workspace_id: workspaceId } }),
  ai: (workspaceId?: string) => apiService.get("/analytics/ai", { params: { workspace_id: workspaceId } }),
  security: () => apiService.get("/analytics/security"),
  notifications: () => apiService.get("/analytics/notifications"),
  benchmarks: (workspaceId?: string) => apiService.get("/analytics/benchmarks", { params: { workspace_id: workspaceId } }),
  dashboard: (params?: { workspaceId?: string; role?: string }) =>
    apiService.get("/analytics/dashboard", { params: { workspace_id: params?.workspaceId, role: params?.role ?? "user" } }),
};

/* -------------------------------------------------------------------------- */
/* Reports                                                                     */
/* -------------------------------------------------------------------------- */

export interface ReportDto {
  id: string;
  name: string;
  kind: string;
  scheduled: boolean;
  filters: Record<string, unknown>;
  lastRunAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export const reportsApi = {
  list: () => apiService.get<{ items: ReportDto[] }>("/reports"),
  kinds: () => apiService.get<string[]>("/reports/kinds"),
  create: (input: { workspaceId: string; name: string; kind: string; scheduled?: boolean; filters?: Record<string, unknown> }) =>
    apiService.post<ReportDto>("/reports", input),
  get: (id: string) => apiService.get<ReportDto>(`/reports/${id}`),
  remove: (id: string) => apiService.delete<{ deleted: boolean }>(`/reports/${id}`),
  run: async (id: string, format: "json" | "csv" | "excel" | "pdf" = "json"): Promise<Blob> => {
    const res = await fetch(`${(import.meta.env.VITE_API_BASE_URL ?? "/api")}/reports/${id}/run?format=${format}`, {
      method: "POST",
      credentials: "include",
    });
    return res.blob();
  },
  runAdHoc: async (kind: string, format: "json" | "csv" | "excel" | "pdf" = "json", workspaceId?: string): Promise<Blob> => {
    const url = new URL(`${(import.meta.env.VITE_API_BASE_URL ?? "/api")}/reports/ad-hoc`);
    url.searchParams.set("kind", kind);
    url.searchParams.set("format", format);
    if (workspaceId) url.searchParams.set("workspace_id", workspaceId);
    const res = await fetch(url.toString(), { method: "POST", credentials: "include" });
    return res.blob();
  },
};

/* -------------------------------------------------------------------------- */
/* Global search                                                               */
/* -------------------------------------------------------------------------- */

export interface SearchHit {
  scope: string;
  id: string;
  title: string;
  subtitle: string | null;
  href: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchHit[];
  counts: Record<string, number>;
  generatedAt: string;
}

export const searchApi = {
  search: (params: { q: string; workspaceId?: string; scopes?: string[]; limit?: number }) =>
    apiService.get<SearchResponse>("/search", {
      params: {
        q: params.q,
        workspace_id: params.workspaceId,
        scopes: params.scopes?.join(","),
        limit: params.limit,
      },
    }),
  suggest: (q: string) => apiService.get<string[]>("/search/suggest", { params: { q } }),
};

/* -------------------------------------------------------------------------- */
/* Media / Upload pipeline                                                     */
/* -------------------------------------------------------------------------- */

export interface MediaDto {
  id: string;
  name: string;
  mimeType: string;
  sizeBytes: number;
  url: string;
  checksum: string | null;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}

export const mediaApi = {
  list: () => apiService.get<{ items: MediaDto[] }>("/media"),
  upload: async (workspaceId: string, file: File, optimize = false) => {
    const form = new FormData();
    form.append("workspace_id", workspaceId);
    form.append("file", file);
    form.append("optimize", String(optimize));
    return apiService.post<MediaDto>("/media", form);
  },
  chunkedUpload: async (workspaceId: string, file: File, chunkSize = 5 * 1024 * 1024, onProgress?: (loaded: number, total: number) => void) => {
    const init = await apiService.post<{ sessionId: string; chunkSize: number }>("/media/chunks/init", {
      workspaceId, name: file.name, mimeType: file.type || "application/octet-stream", totalSize: file.size, chunkSize,
    });
    const size = init.chunkSize ?? chunkSize;
    const chunks = Math.ceil(file.size / size);
    for (let i = 0; i < chunks; i++) {
      const chunk = file.slice(i * size, Math.min(file.size, (i + 1) * size));
      const form = new FormData();
      form.append("index", String(i));
      form.append("file", chunk);
      await apiService.post(`/media/chunks/${init.sessionId}`, form);
      onProgress?.((i + 1) * size, file.size);
    }
    return apiService.post<MediaDto>(`/media/chunks/${init.sessionId}/complete`, { workspace_id: workspaceId });
  },
  signedUrl: (id: string, expiresIn = 3600) =>
    apiService.get<{ url: string; expiresIn: number }>(`/media/${id}/signed-url`, { params: { expires_in: expiresIn } }),
  remove: (id: string) => apiService.delete<{ deleted: boolean }>(`/media/${id}`),
};

/* -------------------------------------------------------------------------- */
/* Notifications                                                               */
/* -------------------------------------------------------------------------- */

export interface NotificationDto {
  id: string;
  title: string;
  message: string;
  category: string;
  priority: string;
  read: boolean;
  archived: boolean;
  href: string | null;
  createdAt: string;
  updatedAt: string;
}

export const notificationsApi = {
  list: () => apiService.get<{ items: NotificationDto[] }>("/notifications"),
  markRead: (id: string) => apiService.post<NotificationDto>(`/notifications/${id}/read`),
  markUnread: (id: string) => apiService.post<NotificationDto>(`/notifications/${id}/unread`),
  readAll: () => apiService.post<{ updated: number }>("/notifications/read-all"),
  digest: () => apiService.get<{ unreadCount: number; byPriority: Record<string, number>; latest: unknown[] }>("/notifications/digest"),
  preferences: () => apiService.get<{ id: string; channel: string; enabled: boolean; quietHours: Record<string, unknown> }[]>("/notifications/preferences"),
};

/* -------------------------------------------------------------------------- */
/* Monitoring extras                                                            */
/* -------------------------------------------------------------------------- */

export const monitoringExtrasApi = {
  system: () => apiService.get("/monitoring/system"),
  database: () => apiService.get("/monitoring/database"),
  metrics: async (): Promise<string> => {
    const res = await fetch(`${(import.meta.env.VITE_API_BASE_URL ?? "/api")}/monitoring/metrics`, { credentials: "include" });
    return res.text();
  },
};
