import { useMemo, useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Archive,
  ArrowUpDown,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Copy,
  Megaphone,
  PauseCircle,
  Plus,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import {
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
import { SectionHeader } from "@/components/common/section-header";
import { StatCard } from "@/components/common/stat-card";
import { DataTableToolbar } from "@/components/common/data-table-toolbar";
import { BulkActionToolbar } from "@/components/common/bulk-action-toolbar";
import { FilterDrawer } from "@/components/common/filter-drawer";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { PermissionGuard } from "@/components/common/permission-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { CampaignStatusBadge } from "@/components/common/campaign-status-badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { campaignService } from "@/services/campaign.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { PERMISSIONS } from "@/constants/rbac";
import {
  CAMPAIGN_CATEGORIES,
  CAMPAIGN_PRIORITIES,
  CAMPAIGN_STATUSES,
  CAMPAIGN_TYPES,
} from "@/constants/campaign";
import type {
  CampaignCategory,
  CampaignListQuery,
  CampaignPriority,
  CampaignStatus,
  CampaignType,
} from "@/types/campaign";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/campaigns/")({
  head: () => ({
    meta: [
      { title: "Campaigns — Multilingua" },
      { name: "description", content: "Plan, launch, and manage multilingual campaigns." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: CampaignsIndexPage,
});

interface Filters {
  status: CampaignStatus[];
  type: CampaignType[];
  priority: CampaignPriority[];
  category: CampaignCategory[];
}
const EMPTY_FILTERS: Filters = { status: [], type: [], priority: [], category: [] };

const PIE_COLORS = ["#2563EB", "#7C3AED", "#DB2777", "#DC2626", "#EA580C", "#CA8A04", "#16A34A", "#0891B2", "#0F766E"];

function CampaignsIndexPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<string>("updatedAt");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [pendingFilters, setPendingFilters] = useState<Filters>(EMPTY_FILTERS);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [confirm, setConfirm] = useState<null | { title: string; action: () => Promise<void> | void; destructive?: boolean }>(null);
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useMemo<CampaignListQuery>(
    () => ({
      page,
      pageSize,
      sortBy,
      sortDir,
      search: debouncedSearch || undefined,
      status: filters.status.length ? filters.status : undefined,
      type: filters.type.length ? filters.type : undefined,
      priority: filters.priority.length ? filters.priority : undefined,
      category: filters.category.length ? filters.category : undefined,
    }),
    [page, pageSize, sortBy, sortDir, debouncedSearch, filters],
  );

  const listQuery = useQuery({ queryKey: ["campaigns", query], queryFn: () => campaignService.list(query), placeholderData: (p) => p });
  const statsQuery = useQuery({ queryKey: ["campaigns", "stats"], queryFn: () => campaignService.getStats() });

  const rows = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const filterCount = filters.status.length + filters.type.length + filters.priority.length + filters.category.length;

  function toggleSort(k: string) {
    if (sortBy === k) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(k); setSortDir("asc"); }
  }
  function toggleRow(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((v) => v !== id) : [...s, id]));
  }
  const allSelected = rows.length > 0 && rows.every((r) => selected.includes(r.id));
  function toggleAll() {
    setSelected((s) => {
      if (allSelected) return s.filter((id) => !rows.some((r) => r.id === id));
      const set = new Set(s);
      rows.forEach((r) => set.add(r.id));
      return [...set];
    });
  }

  async function bulk(action: "archive" | "duplicate" | "delete") {
    if (action === "archive") {
      await campaignService.bulkArchive(selected);
      toast.success(`${selected.length} campaign(s) archived`);
    } else if (action === "duplicate") {
      await campaignService.bulkDuplicate(selected);
      toast.success(`${selected.length} campaign(s) duplicated`);
    } else {
      await campaignService.bulkDelete(selected);
      toast.success(`${selected.length} campaign(s) deleted`);
    }
    setSelected([]);
    qc.invalidateQueries({ queryKey: ["campaigns"] });
  }

  const stats = statsQuery.data;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Campaigns"
        description="Plan, review, and orchestrate every multilingual outreach across channels."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate({ to: "/campaigns/calendar" })} className="gap-2">
              <CalendarDays className="h-4 w-4" /> Calendar
            </Button>
            <PermissionGuard anyOf={[PERMISSIONS.APPROVAL_ACT]}>
              <Button variant="outline" size="sm" onClick={() => navigate({ to: "/campaigns/approvals" })} className="gap-2">
                <ShieldCheck className="h-4 w-4" /> Approvals
                {stats?.pendingApproval ? (
                  <span className="rounded-full bg-amber-500/15 px-1.5 text-[10px] font-semibold text-amber-700 dark:text-amber-400">
                    {stats.pendingApproval}
                  </span>
                ) : null}
              </Button>
            </PermissionGuard>
            <PermissionGuard anyOf={[PERMISSIONS.CAMPAIGN_CREATE]}>
              <Button size="sm" onClick={() => navigate({ to: "/campaigns/new" })} className="gap-2">
                <Plus className="h-4 w-4" /> New campaign
              </Button>
            </PermissionGuard>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <StatCard label="Total" value={String(stats?.total ?? "—")} icon={Megaphone} index={0} />
        <StatCard label="Draft" value={String(stats?.draft ?? "—")} icon={Sparkles} index={1} />
        <StatCard label="Scheduled" value={String(stats?.scheduled ?? "—")} icon={CalendarDays} index={2} />
        <StatCard label="Running" value={String(stats?.running ?? "—")} icon={Megaphone} index={3} />
        <StatCard label="Completed" value={String(stats?.completed ?? "—")} icon={Megaphone} index={4} />
        <StatCard label="Archived" value={String(stats?.archived ?? "—")} icon={Archive} index={5} />
        <StatCard label="Failed" value={String(stats?.failed ?? "—")} icon={Megaphone} index={6} />
        <StatCard label="Cancelled" value={String(stats?.cancelled ?? "—")} icon={PauseCircle} index={7} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2 shadow-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base">Campaign performance</CardTitle>
            <span className="text-xs text-muted-foreground">Live / completed campaigns</span>
          </CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.performance ?? []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="delivered" fill="#2563EB" radius={[6, 6, 0, 0]} />
                <Bar dataKey="opened" fill="#22C55E" radius={[6, 6, 0, 0]} />
                <Bar dataKey="failed" fill="#EF4444" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card className="shadow-card">
          <CardHeader className="pb-2"><CardTitle className="text-base">Type distribution</CardTitle></CardHeader>
          <CardContent className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={stats?.byType ?? []}
                  dataKey="value"
                  nameKey="type"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {(stats?.byType ?? []).map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="shadow-card">
          <CardHeader className="pb-2"><CardTitle className="text-base">Monthly campaigns</CardTitle></CardHeader>
          <CardContent className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.monthly ?? []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#7C3AED" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card className="shadow-card lg:col-span-2">
          <CardHeader className="pb-2"><CardTitle className="text-base">Delivery trend (14d)</CardTitle></CardHeader>
          <CardContent className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={stats?.trend ?? []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="delivered" stroke="#2563EB" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-base">All campaigns</CardTitle>
          <span className="text-xs text-muted-foreground">{total.toLocaleString()} total</span>
        </CardHeader>
        <CardContent className="space-y-4">
          <DataTableToolbar
            search={search}
            onSearchChange={(v) => { setSearch(v); setPage(1); }}
            placeholder="Search by name, code, tag…"
            onOpenFilters={() => { setPendingFilters(filters); setDrawerOpen(true); }}
            filterCount={filterCount}
            onClearFilters={() => { setFilters(EMPTY_FILTERS); setPage(1); }}
          />

          {listQuery.isError ? (
            <ErrorState onRetry={() => listQuery.refetch()} />
          ) : listQuery.isLoading ? (
            <SkeletonBlock rows={8} />
          ) : rows.length === 0 ? (
            <EmptyState title="No campaigns" description="Start by creating a new campaign." />
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="w-10 px-3 py-2">
                      <Checkbox checked={allSelected} onCheckedChange={toggleAll} aria-label="Select all" />
                    </th>
                    <SortHeader label="Campaign" k="name" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                    <th className="px-3 py-2 text-left font-medium">Type</th>
                    <SortHeader label="Status" k="status" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                    <th className="px-3 py-2 text-left font-medium">Owner</th>
                    <SortHeader label="Start" k="updatedAt" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                    <th className="px-3 py-2 text-right font-medium">Reach</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <motion.tr
                      key={row.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.005 }}
                      className={cn("border-t hover:bg-muted/30", selected.includes(row.id) && "bg-primary/5")}
                    >
                      <td className="px-3 py-2">
                        <Checkbox
                          checked={selected.includes(row.id)}
                          onCheckedChange={() => toggleRow(row.id)}
                          aria-label={`Select ${row.name}`}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <Link to="/campaigns/$id" params={{ id: row.id }} className="group flex items-center gap-2">
                          <span className="h-8 w-1 rounded-full" style={{ background: row.color }} />
                          <div className="min-w-0">
                            <p className="truncate font-medium text-foreground group-hover:text-primary">{row.name}</p>
                            <p className="truncate text-xs text-muted-foreground">{row.code}</p>
                          </div>
                        </Link>
                      </td>
                      <td className="px-3 py-2 capitalize text-muted-foreground">{row.type.replace(/_/g, " ")}</td>
                      <td className="px-3 py-2"><CampaignStatusBadge status={row.status} /></td>
                      <td className="px-3 py-2 text-muted-foreground">{row.ownerName}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {row.schedule.startAt ? new Date(row.schedule.startAt).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-3 py-2 text-right font-medium">{row.estimatedReach.toLocaleString()}</td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              Rows per page
              <Select value={String(pageSize)} onValueChange={(v) => { setPageSize(Number(v)); setPage(1); }}>
                <SelectTrigger className="h-8 w-20"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[10, 20, 50, 100].map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Page {page} of {totalPages}</span>
              <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <BulkActionToolbar count={selected.length} onClear={() => setSelected([])}>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={() => bulk("duplicate")}>
          <Copy className="h-4 w-4" /> Duplicate
        </Button>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setConfirm({ title: `Archive ${selected.length} campaign(s)?`, action: () => bulk("archive") })}>
          <Archive className="h-4 w-4" /> Archive
        </Button>
        <PermissionGuard anyOf={[PERMISSIONS.CAMPAIGN_DELETE]}>
          <Button size="sm" variant="destructive" className="gap-1.5" onClick={() => setConfirm({ title: `Delete ${selected.length} campaign(s)?`, action: () => bulk("delete"), destructive: true })}>
            <Trash2 className="h-4 w-4" /> Delete
          </Button>
        </PermissionGuard>
      </BulkActionToolbar>

      <FilterDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onApply={() => { setFilters(pendingFilters); setPage(1); }}
        onReset={() => setPendingFilters(EMPTY_FILTERS)}
      >
        <FilterGroup
          label="Status"
          options={CAMPAIGN_STATUSES.map((s) => ({ value: s.key, label: s.label }))}
          selected={pendingFilters.status}
          onChange={(v) => setPendingFilters((f) => ({ ...f, status: v as CampaignStatus[] }))}
        />
        <FilterGroup
          label="Type"
          options={CAMPAIGN_TYPES.map((t) => ({ value: t.key, label: t.label }))}
          selected={pendingFilters.type}
          onChange={(v) => setPendingFilters((f) => ({ ...f, type: v as CampaignType[] }))}
        />
        <FilterGroup
          label="Priority"
          options={CAMPAIGN_PRIORITIES.map((p) => ({ value: p.key, label: p.label }))}
          selected={pendingFilters.priority}
          onChange={(v) => setPendingFilters((f) => ({ ...f, priority: v as CampaignPriority[] }))}
        />
        <FilterGroup
          label="Category"
          options={CAMPAIGN_CATEGORIES.map((c) => ({ value: c.key, label: c.label }))}
          selected={pendingFilters.category}
          onChange={(v) => setPendingFilters((f) => ({ ...f, category: v as CampaignCategory[] }))}
        />
      </FilterDrawer>

      <ConfirmDialog
        open={!!confirm}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={confirm?.title ?? ""}
        description="This action can be reverted from archives within 30 days."
        confirmLabel="Confirm"
        destructive={confirm?.destructive}
        onConfirm={async () => {
          await confirm?.action();
          setConfirm(null);
        }}
      />
    </div>
  );
}

function SortHeader({
  label, k, sortBy, sortDir, onSort,
}: { label: string; k: string; sortBy: string; sortDir: "asc" | "desc"; onSort: (k: string) => void }) {
  const active = sortBy === k;
  return (
    <th className="px-3 py-2 text-left font-medium">
      <button type="button" onClick={() => onSort(k)} className="inline-flex items-center gap-1 hover:text-foreground">
        {label}
        <ArrowUpDown className={cn("h-3 w-3", active ? "text-primary" : "opacity-40", active && sortDir === "asc" && "rotate-180")} />
      </button>
    </th>
  );
}

function FilterGroup({
  label, options, selected, onChange,
}: { label: string; options: { value: string; label: string }[]; selected: string[]; onChange: (v: string[]) => void }) {
  const toggle = (v: string) =>
    onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v]);
  return (
    <div>
      <Label className="text-xs uppercase tracking-wide text-muted-foreground">{label}</Label>
      <div className="mt-2 flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
        {options.map((opt) => {
          const active = selected.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs transition-colors",
                active ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
