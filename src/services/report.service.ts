import type {
  SavedReport,
  ReportResult,
  ReportKind,
  ExportFormat,
  ExportRequest,
  ExportResult,
  AnalyticsFilters,
  ReportDataset,
} from "@/types/analytics";
import { apiService } from "@/services/api.service";
import { serializeAnalyticsFilters } from "@/services/analytics.service";
import { mockReports, buildReportResult } from "@/lib/mock/platform";

const delay = <T>(v: T, ms = 260): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let reports: SavedReport[] = [...mockReports];

/**
 * Report service — extends the legacy Reports surface with real export
 * endpoints for Phase 6.
 *
 * The legacy CRUD/run/exportCsv/exportJson methods are retained so the
 * existing `/analytics/reports` and `/analytics/builder` routes keep
 * working without modification. The new export methods route through
 * `apiService` and return a signed URL — the frontend never streams
 * binary data itself.
 */
export const reportService = {
  /* -------- legacy (still consumed by /analytics/reports) -------- */
  async list(): Promise<SavedReport[]> {
    return delay([...reports]);
  },
  async get(id: string): Promise<SavedReport | undefined> {
    return delay(reports.find((r) => r.id === id));
  },
  async create(input: Omit<SavedReport, "id" | "createdAt">): Promise<SavedReport> {
    const rec: SavedReport = { ...input, id: `rep-${Date.now()}`, createdAt: new Date().toISOString() };
    reports = [rec, ...reports];
    return delay(rec, 180);
  },
  async duplicate(id: string): Promise<SavedReport> {
    const src = reports.find((r) => r.id === id);
    if (!src) throw new Error("Report not found");
    const rec: SavedReport = { ...src, id: `rep-${Date.now()}`, name: `${src.name} (copy)`, createdAt: new Date().toISOString() };
    reports = [rec, ...reports];
    return delay(rec, 160);
  },
  async remove(id: string): Promise<void> {
    reports = reports.filter((r) => r.id !== id);
    return delay(undefined, 120);
  },
  async run(kind: ReportKind): Promise<ReportResult> {
    return delay(buildReportResult(kind), 380);
  },
  async exportCsv(kind: ReportKind): Promise<string> {
    const result = buildReportResult(kind);
    const header = result.columns.map((c) => c.label).join(",");
    const lines = result.rows.map((r) =>
      result.columns.map((c) => JSON.stringify(r[c.key] ?? "")).join(","),
    );
    return delay([header, ...lines].join("\n"), 220);
  },
  async exportJson(kind: ReportKind): Promise<string> {
    return delay(JSON.stringify(buildReportResult(kind), null, 2), 180);
  },

  /* -------- Phase 6 — Platform Reporting exports -------- */

  /**
   * Request an export of any analytics dataset. The backend generates the
   * file asynchronously and returns a signed URL the client can open or
   * hand to the browser download stack. Supported formats: csv, xlsx, pdf,
   * json.
   */
  export(request: ExportRequest) {
    return apiService.post<ExportResult>("/v1/analytics/exports", {
      dataset: request.dataset,
      format: request.format,
      filters: serializeAnalyticsFilters(request.filters),
    });
  },

  /** Convenience wrapper: same as `export` but returns the URL directly. */
  async exportDataset(
    dataset: ReportDataset,
    format: ExportFormat,
    filters: AnalyticsFilters = {},
  ): Promise<string> {
    const res = await reportService.export({ dataset, format, filters });
    return res.url;
  },
};
