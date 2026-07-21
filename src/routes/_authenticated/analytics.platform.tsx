import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  BarChart3,
  Globe2,
  Languages as LanguagesIcon,
  QrCode,
  Siren,
  Users,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { AnalyticsFilterBar } from "@/components/common/analytics-filter-bar";
import { PermissionGuard } from "@/components/common/permission-guard";
import { RoleGuard } from "@/components/common/role-guard";
import { EmptyState } from "@/components/common/empty-state";
import { ROLES, PERMISSIONS } from "@/constants/rbac";
import { usePermissions } from "@/hooks/use-permissions";
import { analyticsService } from "@/services/analytics.service";
import { reportService } from "@/services/report.service";
import type {
  AnalyticsFilters,
  AnalyticsScope,
  ExportFormat,
  PlatformAnalytics,
  ReportDataset,
} from "@/types/analytics";
import { toast } from "sonner";

/**
 * Phase 6 — Platform Analytics & Reporting.
 *
 * Single reporting center. All module analytics (campaigns / QR / volunteers
 * / disasters / multilingual / public engagement) are aggregated into one
 * response and rendered as scoped sections. RBAC:
 *   - Super Admin    → scope=platform (see everything)
 *   - Campaign Mgr   → scope=organization
 *   - Volunteer      → scope=personal (only "My contribution")
 *   - Viewer         → route is denied by route-access.ts
 */
export const Route = createFileRoute("/_authenticated/analytics/platform")({
  head: () => ({ meta: [{ title: "Platform analytics" }] }),
  component: PlatformAnalyticsPage,
});

const COLORS = ["#2563EB", "#0EA5E9", "#8B5CF6", "#22C55E", "#F59E0B", "#DC2626", "#14B8A6", "#EAB308"];

function PlatformAnalyticsPage() {
  return (
    <RoleGuard
      allow={[ROLES.SUPER_ADMIN, ROLES.CAMPAIGN_MANAGER, ROLES.VOLUNTEER]}
      fallback={<EmptyState title="Analytics not available" description="Your role does not include analytics access." />}
    >
      <PlatformAnalyticsInner />
    </RoleGuard>
  );
}

function PlatformAnalyticsInner() {
  const { hasAnyRole } = usePermissions();
  const scope: AnalyticsScope = hasAnyRole([ROLES.SUPER_ADMIN])
    ? "platform"
    : hasAnyRole([ROLES.CAMPAIGN_MANAGER])
      ? "organization"
      : "personal";

  const [filters, setFilters] = useState<AnalyticsFilters>({});
  const query = useQuery({
    queryKey: ["analytics", "platform", scope, filters],
    queryFn: () => analyticsService.platform(filters),
  });

  const data = query.data;
  const isVolunteer = scope === "personal";

  const handleExport = async (dataset: ReportDataset, format: ExportFormat) => {
    try {
      const url = await reportService.exportDataset(dataset, format, filters);
      window.open(url, "_blank", "noopener");
      toast.success(`Export ready (${format.toUpperCase()})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed");
    }
  };

  return (
    <div className="space-y-5">
      <AnalyticsFilterBar
        value={filters}
        onChange={setFilters}
        exportDataset="platform"
        onExport={(fmt) => handleExport("platform", fmt)}
      />

      {query.isLoading && <LoadingState />}
      {query.isError && (
        <EmptyState
          title="Couldn't load analytics"
          description={query.error instanceof Error ? query.error.message : "Try adjusting filters or reload."}
        />
      )}

      {data && !isVolunteer && <FullAnalyticsSections data={data} onExport={handleExport} />}
      {data && isVolunteer && <PersonalSection data={data} />}
    </div>
  );
}

/* -------------------- Loading placeholder -------------------- */
function LoadingState() {
  return (
    <div className="grid gap-3 md:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="h-24 animate-pulse rounded-xl bg-muted/60" />
      ))}
    </div>
  );
}

/* -------------------- Full analytics (Admin + Manager) -------------------- */
function FullAnalyticsSections({
  data,
  onExport,
}: {
  data: PlatformAnalytics;
  onExport: (d: ReportDataset, f: ExportFormat) => Promise<void>;
}) {
  return (
    <div className="space-y-6">
      <CampaignsSection data={data} onExport={onExport} />
      <QrSection data={data} onExport={onExport} />
      <VolunteersSection data={data} onExport={onExport} />
      <DisastersSection data={data} onExport={onExport} />
      <MultilingualSection data={data} onExport={onExport} />
    </div>
  );
}

/* -------------------- Campaigns -------------------- */
function CampaignsSection({
  data,
  onExport,
}: {
  data: PlatformAnalytics;
  onExport: (d: ReportDataset, f: ExportFormat) => Promise<void>;
}) {
  const c = data.campaigns;
  return (
    <SectionShell title="Campaigns" icon={BarChart3} onExport={(f) => onExport("campaigns", f)}>
      <div className="grid gap-3 md:grid-cols-4">
        <AnalyticsCard label="Total campaigns" value={c.totals.total} icon={BarChart3} />
        <AnalyticsCard label="Published" value={c.totals.published} />
        <AnalyticsCard label="Draft" value={c.totals.draft} />
        <AnalyticsCard label="Archived" value={c.totals.archived} />
        <AnalyticsCard label="Reach" value={c.totals.reach} />
        <AnalyticsCard label="Completion" value={`${Math.round(c.totals.completion * 100)}%`} />
        <AnalyticsCard label="Engagement" value={`${Math.round(c.totals.engagement * 100)}%`} />
        <AnalyticsCard label="Downloads" value={c.totals.downloads} />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Campaign timeline">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={c.timeline}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="published" stroke="#2563EB" />
              <Line type="monotone" dataKey="archived" stroke="#DC2626" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Top campaigns (reach)">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={c.top} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={140} />
              <Tooltip />
              <Bar dataKey="reach" fill="#2563EB" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </SectionShell>
  );
}

/* -------------------- QR -------------------- */
function QrSection({
  data,
  onExport,
}: {
  data: PlatformAnalytics;
  onExport: (d: ReportDataset, f: ExportFormat) => Promise<void>;
}) {
  const q = data.qr;
  return (
    <SectionShell title="QR campaigns" icon={QrCode} onExport={(f) => onExport("qr", f)}>
      <div className="grid gap-3 md:grid-cols-3">
        <AnalyticsCard label="Total scans" value={q.totals.scans} icon={QrCode} />
        <AnalyticsCard label="Unique visitors" value={q.totals.unique} />
        <AnalyticsCard label="Repeat visitors" value={q.totals.repeat} />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Daily trend">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={q.trend}>
              <defs>
                <linearGradient id="qr-scans" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#0EA5E9" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#0EA5E9" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="scans" stroke="#0EA5E9" fill="url(#qr-scans)" />
              <Area type="monotone" dataKey="unique" stroke="#2563EB" fillOpacity={0} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Device distribution">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={q.byDevice} dataKey="value" nameKey="label" outerRadius={80} label>
                {q.byDevice.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Top countries">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={q.byCountry}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#8B5CF6" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Top languages">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={q.byLanguage}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#22C55E" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </SectionShell>
  );
}

/* -------------------- Volunteers -------------------- */
function VolunteersSection({
  data,
  onExport,
}: {
  data: PlatformAnalytics;
  onExport: (d: ReportDataset, f: ExportFormat) => Promise<void>;
}) {
  const v = data.volunteers;
  return (
    <SectionShell title="Volunteers" icon={Users} onExport={(f) => onExport("volunteers", f)}>
      <div className="grid gap-3 md:grid-cols-5">
        <AnalyticsCard label="Registered" value={v.totals.registered} icon={Users} />
        <AnalyticsCard label="Available" value={v.totals.available} />
        <AnalyticsCard label="Assigned" value={v.totals.assigned} />
        <AnalyticsCard label="Completed tasks" value={v.totals.completedTasks} />
        <AnalyticsCard label="Avg. completion (h)" value={v.totals.averageCompletionHours.toFixed(1)} />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Volunteer activity">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={v.activity}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="assigned" stroke="#F59E0B" />
              <Line type="monotone" dataKey="completed" stroke="#22C55E" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Top contributors">
          <div className="space-y-2">
            {v.topContributors.map((t, i) => (
              <div key={t.id} className="flex items-center justify-between rounded-md border p-2">
                <div className="flex items-center gap-2 text-sm">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                    {i + 1}
                  </span>
                  <span className="font-medium">{t.name}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {t.completedTasks} tasks · {t.hoursContributed.toFixed(1)}h
                </div>
              </div>
            ))}
            {v.topContributors.length === 0 && (
              <p className="text-sm text-muted-foreground">No contributions yet.</p>
            )}
          </div>
        </ChartCard>
      </div>
    </SectionShell>
  );
}

/* -------------------- Disasters -------------------- */
function DisastersSection({
  data,
  onExport,
}: {
  data: PlatformAnalytics;
  onExport: (d: ReportDataset, f: ExportFormat) => Promise<void>;
}) {
  const d = data.disasters;
  return (
    <SectionShell title="Disasters" icon={Siren} onExport={(f) => onExport("disasters", f)}>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <AnalyticsCard label="Active" value={d.totals.active} icon={Siren} />
        <AnalyticsCard label="Resolved" value={d.totals.resolved} />
        <AnalyticsCard label="Volunteers assigned" value={d.totals.volunteersAssigned} />
        <AnalyticsCard label="Emergency campaigns" value={d.totals.emergencyCampaigns} />
        <AnalyticsCard label="Public alert reach" value={d.totals.publicAlertReach} />
        <AnalyticsCard label="Avg. response (h)" value={d.totals.averageResponseHours.toFixed(1)} />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Disaster timeline">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={d.timeline}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="opened" stroke="#DC2626" />
              <Line type="monotone" dataKey="resolved" stroke="#22C55E" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Severity distribution">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={d.bySeverity} dataKey="value" nameKey="label" outerRadius={80} label>
                {d.bySeverity.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </SectionShell>
  );
}

/* -------------------- Multilingual -------------------- */
function MultilingualSection({
  data,
  onExport,
}: {
  data: PlatformAnalytics;
  onExport: (d: ReportDataset, f: ExportFormat) => Promise<void>;
}) {
  const m = data.multilingual;
  const mostUsed = m.mostUsedLanguage ?? (m.byLanguage[0]?.label ?? "—");
  return (
    <SectionShell title="Multilingual & AI" icon={LanguagesIcon} onExport={(f) => onExport("multilingual", f)}>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <AnalyticsCard label="Languages used" value={m.totals.languagesUsed} icon={Globe2} />
        <AnalyticsCard label="Translations" value={m.totals.translationsGenerated} />
        <AnalyticsCard label="Published" value={m.totals.translationsPublished} />
        <AnalyticsCard label="Audio generated" value={m.totals.audioGenerated} />
        <AnalyticsCard label="Audio plays" value={m.totals.audioPlays} />
        <AnalyticsCard label="Coverage" value={`${Math.round(m.totals.coverage * 100)}%`} helper={`Most used: ${mostUsed}`} />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Translations by language">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={m.byLanguage}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#8B5CF6" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Translation status">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={m.byStatus} dataKey="value" nameKey="label" outerRadius={80} label>
                {m.byStatus.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </SectionShell>
  );
}

/* -------------------- Personal (Volunteer) -------------------- */
function PersonalSection({ data }: { data: PlatformAnalytics }) {
  const p = data.personal;
  if (!p) {
    return <EmptyState title="No contribution data yet" description="Complete a task to see your personal analytics." />;
  }
  return (
    <SectionShell title="My contribution" icon={Activity}>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <AnalyticsCard label="Assigned tasks" value={p.totals.assignedTasks} icon={Activity} />
        <AnalyticsCard label="Completed tasks" value={p.totals.completedTasks} />
        <AnalyticsCard label="Hours contributed" value={p.totals.hoursContributed.toFixed(1)} />
        <AnalyticsCard label="Campaigns" value={p.totals.campaignsSupported} />
        <AnalyticsCard label="Disasters" value={p.totals.disastersSupported} />
        <AnalyticsCard label="Languages" value={p.totals.languagesContributed} />
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Activity">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={p.activity}>
              <defs>
                <linearGradient id="pers" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#22C55E" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#22C55E" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="completed" stroke="#22C55E" fill="url(#pers)" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Recent activity">
          <div className="space-y-2">
            {p.recent.map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-md border p-2 text-sm">
                <span className="font-medium">{r.title}</span>
                <span className="text-xs text-muted-foreground capitalize">{r.kind}</span>
              </div>
            ))}
            {p.recent.length === 0 && (
              <p className="text-sm text-muted-foreground">No recent activity.</p>
            )}
          </div>
        </ChartCard>
      </div>
    </SectionShell>
  );
}

/* -------------------- Reusable primitives -------------------- */
function SectionShell({
  title,
  icon: Icon,
  onExport,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  onExport?: (f: ExportFormat) => Promise<void> | void;
  children: React.ReactNode;
}) {
  const [busy, setBusy] = useState<ExportFormat | null>(null);
  const run = async (f: ExportFormat) => {
    if (!onExport) return;
    setBusy(f);
    try {
      await onExport(f);
    } finally {
      setBusy(null);
    }
  };
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {title}
        </h2>
        {onExport && (
          <PermissionGuard anyOf={[PERMISSIONS.ANALYTICS_EXPORT]}>
            <div className="flex gap-1">
              {(["csv", "xlsx", "pdf"] as ExportFormat[]).map((f) => (
                <button
                  key={f}
                  type="button"
                  disabled={busy !== null}
                  onClick={() => run(f)}
                  className="rounded-md border px-2 py-1 text-xs font-medium hover:bg-accent disabled:opacity-50"
                >
                  {busy === f ? "…" : f.toUpperCase()}
                </button>
              ))}
            </div>
          </PermissionGuard>
        )}
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
