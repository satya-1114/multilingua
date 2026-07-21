// ─────────────────────────────────────────────────────────────────────────────
// Phase 6.5 — Analytics Platform (Metrics / Snapshots / Reports)
// ─────────────────────────────────────────────────────────────────────────────

export type MetricScope =
  | "volunteer"
  | "disaster"
  | "public_resource"
  | "translation"
  | "organization"
  | "platform";

export interface AnalyticsMetric {
  id: string;
  metricName: string;
  metricScope: MetricScope | string;
  entityType: string | null;
  entityId: string | null;
  metricValue: number;
  metricUnit: string | null;
  recordedAt: string;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface AnalyticsMetricInput {
  metricName: string;
  metricScope: MetricScope | string;
  metricValue: number;
  recordedAt: string;
  entityType?: string | null;
  entityId?: string | null;
  metricUnit?: string | null;
  metadata?: Record<string, unknown>;
}

export interface MetricListQuery {
  q?: string;
  metricScope?: string;
  metricName?: string;
  entityType?: string;
  entityId?: string;
  recordedFrom?: string;
  recordedTo?: string;
  page?: number;
  pageSize?: number;
}

export type SnapshotType = "daily" | "weekly" | "monthly" | "custom";

export interface AnalyticsSnapshot {
  id: string;
  snapshotType: SnapshotType | string;
  organizationId: string | null;
  periodStart: string;
  periodEnd: string;
  generatedAt: string;
  metricsJson: Record<string, unknown>;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface AnalyticsSnapshotInput {
  snapshotType: SnapshotType | string;
  periodStart: string;
  periodEnd: string;
  metricsJson?: Record<string, unknown>;
  organizationId?: string | null;
  metadata?: Record<string, unknown>;
}

export type ReportStatus = "pending" | "generating" | "completed" | "failed" | "expired";

export interface AnalyticsReport {
  id: string;
  reportName: string;
  reportType: string;
  requestedByUserId: string | null;
  organizationId: string | null;
  status: ReportStatus | string;
  filePath: string | null;
  generatedAt: string | null;
  expiresAt: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface AnalyticsReportInput {
  reportName: string;
  reportType: string;
  requestedByUserId?: string | null;
  organizationId?: string | null;
  metadata?: Record<string, unknown>;
}

export interface SnapshotListQuery {
  snapshotType?: string;
  organizationId?: string;
  page?: number;
  pageSize?: number;
}

export interface ReportListQuery {
  status?: string;
  reportType?: string;
  organizationId?: string;
  requestedByUserId?: string;
  page?: number;
  pageSize?: number;
}

export interface MetricAggregate {
  count: number;
  sum: number;
  avg: number;
  min: number;
  max: number;
}

export interface PlatformOverviewKpis {
  totalVolunteers: number;
  activeDisasters: number;
  publicResources: number;
  publishedTranslations: number;
  organizations: number;
  reportsGenerated: number;
}

export interface KpiPoint {
  label: string;
  value: number;
  delta?: number;
  helper?: string;
}

export interface TimeSeriesPoint {
  date: string;
  [metric: string]: string | number;
}

export interface DistributionSlice {
  label: string;
  value: number;
  color?: string;
}

export interface ExecutiveOverview {
  kpis: KpiPoint[];
  reach: TimeSeriesPoint[];
  audienceGrowth: TimeSeriesPoint[];
  languages: DistributionSlice[];
  organizations: DistributionSlice[];
  engagement: TimeSeriesPoint[];
  delivery: TimeSeriesPoint[];
  activity: TimeSeriesPoint[];
  approvals: KpiPoint[];
}

export type ReportKind =
  | "campaign"
  | "audience"
  | "organization"
  | "delivery"
  | "template"
  | "translation"
  | "ai"
  | "audit"
  | "security"
  | "activity";

export interface SavedReport {
  id: string;
  name: string;
  kind: ReportKind;
  description: string;
  createdBy: string;
  createdAt: string;
  lastRunAt?: string;
  filters: Record<string, string | number | string[] | undefined>;
  scheduled?: boolean;
}

export interface ReportRow {
  id: string;
  [column: string]: string | number;
}

export interface ReportResult {
  columns: { key: string; label: string; kind: "text" | "number" | "date" }[];
  rows: ReportRow[];
  total: number;
}

/* ================================================================== */
/* Phase 6 — Platform Analytics & Reporting                            */
/* ------------------------------------------------------------------ */
/* Single aggregate model for the unified reporting center. Every    */
/* module surface (campaigns, qr, volunteers, disasters, multilingual */
/* public) is a namespaced block on the same response so the UI can  */
/* filter it in a single query. Backend contract lives in            */
/* docs/BACKEND-ANALYTICS.md.                                        */
/* ================================================================== */

export type AnalyticsScope = "platform" | "organization" | "personal";

export interface AnalyticsFilters {
  from?: string; // ISO date
  to?: string;   // ISO date
  campaignIds?: string[];
  disasterIds?: string[];
  organizationIds?: string[];
  languages?: string[];
  volunteerIds?: string[];
}

export interface CampaignAnalytics {
  totals: {
    total: number;
    published: number;
    draft: number;
    archived: number;
    reach: number;
    completion: number;    // 0..1 — average completion
    engagement: number;    // 0..1 — average engagement rate
    downloads: number;
  };
  top: {
    id: string;
    name: string;
    reach: number;
    engagement: number;
  }[];
  timeline: TimeSeriesPoint[]; // { date, published, archived }
}

export interface QrAnalyticsAggregate {
  totals: {
    scans: number;
    unique: number;
    repeat: number;
  };
  byCountry: DistributionSlice[];
  byLanguage: DistributionSlice[];
  byDevice: DistributionSlice[];
  trend: TimeSeriesPoint[]; // { date, scans, unique }
}

export interface VolunteerAnalytics {
  totals: {
    registered: number;
    available: number;
    assigned: number;
    completedTasks: number;
    averageCompletionHours: number;
  };
  activity: TimeSeriesPoint[]; // { date, assigned, completed }
  topContributors: {
    id: string;
    name: string;
    completedTasks: number;
    hoursContributed: number;
  }[];
}

export interface DisasterAnalytics {
  totals: {
    active: number;
    resolved: number;
    volunteersAssigned: number;
    emergencyCampaigns: number;
    publicAlertReach: number;
    averageResponseHours: number;
  };
  bySeverity: DistributionSlice[];
  timeline: TimeSeriesPoint[]; // { date, opened, resolved }
}

export interface MultilingualAnalytics {
  totals: {
    languagesUsed: number;
    translationsGenerated: number;
    translationsPublished: number;
    audioGenerated: number;
    audioPlays: number;
    coverage: number; // 0..1 — percent of entities with >=1 non-source language published
  };
  byLanguage: DistributionSlice[]; // count of published translations per language
  byStatus: DistributionSlice[];   // draft/generated/edited/published
  mostUsedLanguage?: string;
}

/** Personal contribution snapshot for the Volunteer analytics dashboard. */
export interface PersonalAnalytics {
  totals: {
    assignedTasks: number;
    completedTasks: number;
    hoursContributed: number;
    campaignsSupported: number;
    disastersSupported: number;
    languagesContributed: number;
  };
  activity: TimeSeriesPoint[]; // { date, completed }
  recent: {
    id: string;
    title: string;
    kind: "task" | "translation" | "audio";
    completedAt: string;
  }[];
}

/** Unified platform analytics response — one call per dashboard render. */
export interface PlatformAnalytics {
  scope: AnalyticsScope;
  range: { from: string; to: string };
  campaigns: CampaignAnalytics;
  qr: QrAnalyticsAggregate;
  volunteers: VolunteerAnalytics;
  disasters: DisasterAnalytics;
  multilingual: MultilingualAnalytics;
  personal?: PersonalAnalytics; // present when scope="personal"
}

export type ExportFormat = "csv" | "xlsx" | "pdf" | "json";

export type ReportDataset =
  | "campaigns"
  | "qr"
  | "volunteers"
  | "disasters"
  | "multilingual"
  | "public_engagement"
  | "platform";

export interface ExportRequest {
  dataset: ReportDataset;
  format: ExportFormat;
  filters: AnalyticsFilters;
}

/** Signed URL response — the frontend never streams binary data itself. */
export interface ExportResult {
  url: string;
  format: ExportFormat;
  dataset: ReportDataset;
  expiresAt: string;
  sizeBytes?: number;
}
