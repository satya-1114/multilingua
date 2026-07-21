import { apiService } from "./api.service";
import { httpClient } from "@/api/client/http-client";
import { environmentService } from "./environment.service";
import type { Paginated } from "@/types/common";
import type {
  PublicResource,
  PublicResourceCreateInput,
  PublicResourceListQuery,
  PublicResourceUpdateInput,
  PublicView,
  PublicViewSummary,
  QRCode,
  QRCodeCreateInput,
  QRStatus,
  Visibility,
} from "@/types/public-access";

/**
 * Public Information & QR service.
 *
 * Authenticated management endpoints are mounted under `/public-resources`
 * (see `backend/app/api/v1/public_access.py`). Anonymous resolution endpoints
 * live outside the versioned API at `/api/public/*` — for those we build an
 * absolute URL from `VITE_API_BASE_URL`.
 */

function publicBase(): string {
  const base = environmentService.get("API_BASE_URL").replace(/\/+$/, "");
  if (/\/v\d+$/.test(base)) return base.replace(/\/v\d+$/, "/public");
  return `${base}/public`;
}


function publicUrl(path: string): string {
  const base = publicBase();
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

export const publicAccessService = {
  // ── Resources ─────────────────────────────────────────────────────────
  async list(
    query: PublicResourceListQuery = {},
  ): Promise<Paginated<PublicResource>> {
    const env = await httpClient.request<PublicResource[]>({
      method: "GET",
      path: "/public-resources",
      params: query as Record<string, string | number | boolean | undefined>,
    });
    const items = Array.isArray(env.data) ? env.data : [];
    const pg = env.pagination;
    return {
      items,
      total: pg?.total ?? items.length,
      page: pg?.page ?? query.page ?? 1,
      pageSize: pg?.pageSize ?? query.pageSize ?? items.length,
    };
  },

  get(id: string): Promise<PublicResource> {
    return apiService.get<PublicResource>(`/public-resources/${id}`);
  },

  create(input: PublicResourceCreateInput): Promise<PublicResource> {
    return apiService.post<PublicResource>("/public-resources", input);
  },

  update(id: string, patch: PublicResourceUpdateInput): Promise<PublicResource> {
    return apiService.patch<PublicResource>(`/public-resources/${id}`, patch);
  },

  publish(id: string): Promise<PublicResource> {
    return apiService.post<PublicResource>(`/public-resources/${id}/publish`);
  },
  unpublish(id: string, to?: Visibility): Promise<PublicResource> {
    return apiService.post<PublicResource>(
      `/public-resources/${id}/unpublish`,
      to ? { to } : {},
    );
  },
  expire(id: string): Promise<PublicResource> {
    return apiService.post<PublicResource>(`/public-resources/${id}/expire`);
  },
  regenerateSlug(id: string, slug: string): Promise<PublicResource> {
    return apiService.post<PublicResource>(
      `/public-resources/${id}/regenerate-slug`,
      { slug },
    );
  },
  regenerateQrToken(id: string): Promise<PublicResource> {
    return apiService.post<PublicResource>(
      `/public-resources/${id}/regenerate-qr-token`,
    );
  },

  // ── QR metadata ───────────────────────────────────────────────────────
  listQr(id: string, status?: QRStatus): Promise<QRCode[]> {
    return apiService.get<QRCode[]>(
      `/public-resources/${id}/qr`,
      status ? { params: { status } } : undefined,
    );
  },
  createQr(id: string, payload: QRCodeCreateInput = {}): Promise<QRCode> {
    return apiService.post<QRCode>(`/public-resources/${id}/qr`, payload);
  },
  activateQr(qrId: string): Promise<QRCode> {
    return apiService.patch<QRCode>(`/public-resources/qr/${qrId}/activate`);
  },
  deactivateQr(qrId: string, status?: QRStatus): Promise<QRCode> {
    return apiService.patch<QRCode>(
      `/public-resources/qr/${qrId}/deactivate`,
      status ? { status } : {},
    );
  },
  regenerateQr(
    qrId: string,
    payload: Record<string, unknown> = {},
  ): Promise<QRCode> {
    return apiService.patch<QRCode>(
      `/public-resources/qr/${qrId}/regenerate`,
      payload,
    );
  },

  // ── Views ─────────────────────────────────────────────────────────────
  listViews(id: string, limit = 100): Promise<PublicView[]> {
    return apiService.get<PublicView[]>(`/public-resources/${id}/views`, {
      params: { limit },
    });
  },
  viewsSummary(id: string): Promise<PublicViewSummary> {
    return apiService.get<PublicViewSummary>(
      `/public-resources/${id}/views/summary`,
    );
  },

  // ── Anonymous (public) ────────────────────────────────────────────────
  async resolveBySlug(slug: string): Promise<PublicResource> {
    const env = await httpClient.request<PublicResource>({
      method: "GET",
      path: publicUrl(`/p/${encodeURIComponent(slug)}`),
    });
    return env.data;
  },
  async resolveByToken(token: string): Promise<PublicResource> {
    const env = await httpClient.request<PublicResource>({
      method: "GET",
      path: publicUrl(`/q/${encodeURIComponent(token)}`),
    });
    return env.data;
  },
  async registerViewBySlug(
    slug: string,
    payload: Record<string, unknown> = {},
  ): Promise<{ registered: boolean; view?: PublicView; reason?: string }> {
    const env = await httpClient.request<{
      registered: boolean;
      view?: PublicView;
      reason?: string;
    }>({
      method: "POST",
      path: publicUrl(`/p/${encodeURIComponent(slug)}/view`),
      body: payload,
    });
    return env.data;
  },
  async registerViewByToken(
    token: string,
    payload: Record<string, unknown> = {},
  ): Promise<{ registered: boolean; view?: PublicView; reason?: string }> {
    const env = await httpClient.request<{
      registered: boolean;
      view?: PublicView;
      reason?: string;
    }>({
      method: "POST",
      path: publicUrl(`/q/${encodeURIComponent(token)}/view`),
      body: payload,
    });
    return env.data;
  },
};
