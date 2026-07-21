import type {
  AnalyticsFilters,
  AnalyticsMetric,
  AnalyticsMetricInput,
  AnalyticsReport,
  AnalyticsReportInput,
  AnalyticsSnapshot,
  AnalyticsSnapshotInput,
  ExecutiveOverview,
  MetricAggregate,
  MetricListQuery,
  PlatformAnalytics,
  PlatformOverviewKpis,
  ReportListQuery,
  SnapshotListQuery,
} from "@/types/analytics";
import type { Paginated } from "@/types/common";
import { apiService } from "@/services/api.service";
import { httpClient } from "@/api/client/http-client";
import { mockExecutive } from "@/lib/mock/platform";
import { volunteerService } from "@/services/volunteer.service";
import { disasterService } from "@/services/disaster.service";
import { publicAccessService } from "@/services/public-access.service";
import { organizationService } from "@/services/organization.service";


const delay = <T>(v: T, ms = 260): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

const BASE = "/v1/analytics";
type Params = Record<string, string | number | boolean | undefined>;

async function listPaginated<T>(path: string, params: Params): Promise<Paginated<T>> {
  const env = await httpClient.request<T[]>({ method: "GET", path, params });
  const items = Array.isArray(env.data) ? env.data : [];
  const pg = env.pagination;
  return {
    items,
    total: pg?.total ?? items.length,
    page: pg?.page ?? Number(params.page ?? 1),
    pageSize: pg?.pageSize ?? Number(params.pageSize ?? items.length),
  };
}


/**
 * Analytics service — single reporting center facade.
 *
 * `overview()` is retained for backward compatibility with the legacy
 * Executive Overview route. Every Phase 6 method is a thin wrapper over
 * `apiService`; there is no separate HTTP client, no hardcoded fixtures,
 * and no per-module analytics implementation. Backend contract:
 * `docs/BACKEND-ANALYTICS.md`.
 */
export const analyticsService = {
  /** Legacy executive overview — used by /analytics (index). */
  async overview(): Promise<ExecutiveOverview> {
    return delay(mockExecutive);
  },

  /**
   * Aggregate platform analytics scoped by the caller's role.
   * The backend enforces the effective scope:
   *   - Super Admin    → scope=platform
   *   - Campaign Mgr   → scope=organization
   *   - Volunteer      → scope=personal
   */
  platform(filters: AnalyticsFilters = {}) {
    return apiService.get<PlatformAnalytics>(`${BASE}/platform`, {
      params: serializeFilters(filters),
    });
  },

  // ─── Platform overview KPIs (fan-out to module list endpoints) ────────
  async platformOverview(): Promise<PlatformOverviewKpis> {
    const safe = async <T>(p: Promise<T>, fallback: T): Promise<T> => {
      try {
        return await p;
      } catch {
        return fallback;
      }
    };
    const empty = { items: [], total: 0, page: 1, pageSize: 1 };
    const [vols, dis, res, orgs, reps, transAgg] = await Promise.all([
      safe(volunteerService.list({ pageSize: 1 } as never), empty),
      safe(disasterService.list({ pageSize: 1, status: "active" } as never), empty),
      safe(publicAccessService.list({ pageSize: 1 } as never), empty),
      safe(organizationService.list({ pageSize: 1 } as never), empty),
      safe(this.listReports({ pageSize: 1, status: "completed" }), empty as Paginated<AnalyticsReport>),
      safe(this.aggregateMetric({ metricName: "translation.published", metricScope: "translation" }), {
        count: 0, sum: 0, avg: 0, min: 0, max: 0,
      } as MetricAggregate),
    ]);
    return {
      totalVolunteers: vols.total,
      activeDisasters: dis.total,
      publicResources: res.total,
      publishedTranslations: Math.round(transAgg.sum || transAgg.count || 0),
      organizations: orgs.total,
      reportsGenerated: reps.total,
    };
  },

  // ─── Metrics ──────────────────────────────────────────────────────────
  listMetrics(q: MetricListQuery = {}) {
    return listPaginated<AnalyticsMetric>(`${BASE}/metrics`, {
      q: q.q,
      metric_scope: q.metricScope,
      metric_name: q.metricName,
      entity_type: q.entityType,
      entity_id: q.entityId,
      recorded_from: q.recordedFrom,
      recorded_to: q.recordedTo,
      page: q.page,
      page_size: q.pageSize,
    });
  },
  getMetric(id: string) {
    return apiService.get<AnalyticsMetric>(`${BASE}/metrics/${id}`);
  },
  createMetric(input: AnalyticsMetricInput) {
    return apiService.post<AnalyticsMetric>(`${BASE}/metrics`, input);
  },
  updateMetric(id: string, patch: Partial<AnalyticsMetricInput>) {
    return apiService.patch<AnalyticsMetric>(`${BASE}/metrics/${id}`, patch);
  },
  deleteMetric(id: string) {
    return apiService.delete<{ id: string; deleted: boolean }>(`${BASE}/metrics/${id}`);
  },
  aggregateMetric(params: {
    metricName: string;
    metricScope?: string;
    recordedFrom?: string;
    recordedTo?: string;
  }) {
    return apiService.get<MetricAggregate>(`${BASE}/metrics/aggregate`, {
      params: {
        metric_name: params.metricName,
        metric_scope: params.metricScope,
        recorded_from: params.recordedFrom,
        recorded_to: params.recordedTo,
      },
    });
  },

  // ─── Snapshots ────────────────────────────────────────────────────────
  listSnapshots(q: SnapshotListQuery = {}) {
    return listPaginated<AnalyticsSnapshot>(`${BASE}/snapshots`, {
      snapshot_type: q.snapshotType,
      organization_id: q.organizationId,
      page: q.page,
      page_size: q.pageSize,
    });
  },
  getSnapshot(id: string) {
    return apiService.get<AnalyticsSnapshot>(`${BASE}/snapshots/${id}`);
  },
  createSnapshot(input: AnalyticsSnapshotInput) {
    return apiService.post<AnalyticsSnapshot>(`${BASE}/snapshots`, input);
  },
  regenerateSnapshot(id: string) {
    return apiService.post<AnalyticsSnapshot>(`${BASE}/snapshots/${id}/regenerate`);
  },
  deleteSnapshot(id: string) {
    return apiService.delete<{ id: string; deleted: boolean }>(`${BASE}/snapshots/${id}`);
  },

  // ─── Reports ──────────────────────────────────────────────────────────
  listReports(q: ReportListQuery = {}) {
    return listPaginated<AnalyticsReport>(`${BASE}/reports`, {
      status: q.status,
      report_type: q.reportType,
      organization_id: q.organizationId,
      requested_by_user_id: q.requestedByUserId,
      page: q.page,
      page_size: q.pageSize,
    });
  },
  getReport(id: string) {
    return apiService.get<AnalyticsReport>(`${BASE}/reports/${id}`);
  },
  requestReport(input: AnalyticsReportInput) {
    return apiService.post<AnalyticsReport>(`${BASE}/reports`, input);
  },
  startReport(id: string) {
    return apiService.post<AnalyticsReport>(`${BASE}/reports/${id}/start`);
  },
  completeReport(id: string, filePath?: string) {
    return apiService.post<AnalyticsReport>(`${BASE}/reports/${id}/complete`, { filePath });
  },
  failReport(id: string, reason?: string) {
    return apiService.post<AnalyticsReport>(`${BASE}/reports/${id}/fail`, { reason });
  },
  expireReport(id: string) {
    return apiService.post<AnalyticsReport>(`${BASE}/reports/${id}/expire`);
  },
  deleteReport(id: string) {
    return apiService.delete<{ id: string; deleted: boolean }>(`${BASE}/reports/${id}`);
  },
};

/** Serialise structured filter arrays into the flat query params apiService accepts. */
function serializeFilters(f: AnalyticsFilters): Record<string, string | number | boolean | undefined> {
  const out: Record<string, string | number | boolean | undefined> = {};
  if (f.from) out.from = f.from;
  if (f.to) out.to = f.to;
  if (f.campaignIds?.length) out.campaign_ids = f.campaignIds.join(",");
  if (f.disasterIds?.length) out.disaster_ids = f.disasterIds.join(",");
  if (f.organizationIds?.length) out.organization_ids = f.organizationIds.join(",");
  if (f.languages?.length) out.languages = f.languages.join(",");
  if (f.volunteerIds?.length) out.volunteer_ids = f.volunteerIds.join(",");
  return out;
}

export { serializeFilters as serializeAnalyticsFilters };
