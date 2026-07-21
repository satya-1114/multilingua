import { useMemo, useState } from "react";
import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Download,
  Plus,
  Trash2,
  Upload,
  Users,
  UserCheck,
  UserX,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { StatCard } from "@/components/common/stat-card";
import { StatusBadge } from "@/components/common/status-badge";
import { AudienceAvatar } from "@/components/common/audience-avatar";
import { DataTableToolbar } from "@/components/common/data-table-toolbar";
import { BulkActionToolbar } from "@/components/common/bulk-action-toolbar";
import { FilterDrawer } from "@/components/common/filter-drawer";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { PermissionGuard } from "@/components/common/permission-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { CsvUploadDialog } from "@/components/common/csv-upload-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { audienceService } from "@/services/audience.service";
import { tagService } from "@/services/tag.service";
import { csvService } from "@/services/csv.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { PERMISSIONS } from "@/constants/rbac";
import { COMMUNICATION_CHANNELS, INDIAN_STATES, LANGUAGES } from "@/constants/india";
import type { AudienceListQuery, AudienceStatus } from "@/types/audience";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/audience/")({
  head: () => ({
    meta: [
      { title: "Audience — Multilingua" },
      { name: "description", content: "Manage your audience contacts and segments." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AudienceListPage,
});

interface Filters {
  status: AudienceStatus[];
  states: string[];
  languages: string[];
  channels: string[];
}

const EMPTY_FILTERS: Filters = { status: [], states: [], languages: [], channels: [] };

function AudienceListPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sortBy, setSortBy] = useState<string>("updatedAt");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [pendingFilters, setPendingFilters] = useState<Filters>(EMPTY_FILTERS);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [importOpen, setImportOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useMemo<AudienceListQuery>(
    () => ({
      page, pageSize, sortBy, sortDir,
      search: debouncedSearch || undefined,
      status: filters.status.length ? filters.status : undefined,
      states: filters.states.length ? filters.states : undefined,
      languages: filters.languages.length ? filters.languages : undefined,
      channels: filters.channels.length ? filters.channels : undefined,
    }),
    [page, pageSize, sortBy, sortDir, debouncedSearch, filters],
  );

  const listQuery = useQuery({
    queryKey: ["audience", query],
    queryFn: () => audienceService.list(query),
    placeholderData: (prev) => prev,
  });

  const statsQuery = useQuery({ queryKey: ["audience", "stats"], queryFn: () => audienceService.getStats() });
  const tagsQuery = useQuery({ queryKey: ["audience", "tags"], queryFn: () => tagService.list() });

  const filterCount = filters.status.length + filters.states.length + filters.languages.length + filters.channels.length;
  const rows = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  function toggleSort(key: string) {
    if (sortBy === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(key); setSortDir("asc"); }
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

  async function bulkDelete() {
    await audienceService.bulkRemove(selected);
    toast.success(`${selected.length} contact(s) archived`);
    setSelected([]); setDeleteOpen(false);
    qc.invalidateQueries({ queryKey: ["audience"] });
  }

  async function bulkStatus(status: AudienceStatus) {
    await audienceService.bulkUpdateStatus(selected, status);
    toast.success(`Status updated for ${selected.length} contact(s)`);
    setSelected([]);
    qc.invalidateQueries({ queryKey: ["audience"] });
  }

  async function exportAll() {
    const items = await audienceService.listAll(query);
    await csvService.exportAudience(items);
    toast.success(`Exported ${items.length} contacts`);
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Audience"
        description="Search, segment, and manage every contact across your organization."
        actions={
          <div className="flex flex-wrap gap-2">
            <PermissionGuard anyOf={[PERMISSIONS.AUDIENCE_EXPORT]}>
              <Button variant="outline" size="sm" onClick={exportAll} className="gap-2">
                <Download className="h-4 w-4" /> Export
              </Button>
            </PermissionGuard>
            <PermissionGuard anyOf={[PERMISSIONS.AUDIENCE_IMPORT]}>
              <Button variant="outline" size="sm" onClick={() => setImportOpen(true)} className="gap-2">
                <Upload className="h-4 w-4" /> Import CSV
              </Button>
            </PermissionGuard>
            <PermissionGuard anyOf={[PERMISSIONS.AUDIENCE_CREATE]}>
              <Button size="sm" onClick={() => navigate({ to: "/audience/new" })} className="gap-2">
                <Plus className="h-4 w-4" /> Add contact
              </Button>
            </PermissionGuard>
          </div>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total audience" value={String(statsQuery.data?.total ?? "—")} icon={Users} index={0} />
        <StatCard label="Active" value={String(statsQuery.data?.active ?? "—")} icon={UserCheck} index={1} />
        <StatCard label="Inactive" value={String(statsQuery.data?.inactive ?? "—")} icon={UserX} index={2} />
        <StatCard label="Recently added (14d)" value={String(statsQuery.data?.recentlyAdded ?? "—")} icon={Sparkles} index={3} />
      </div>

      <Card className="shadow-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-base">Contacts</CardTitle>
          <span className="text-xs text-muted-foreground">{total.toLocaleString()} total</span>
        </CardHeader>
        <CardContent className="space-y-4">
          <DataTableToolbar
            search={search}
            onSearchChange={(v) => { setSearch(v); setPage(1); }}
            placeholder="Search by name, email, phone, city…"
            onOpenFilters={() => { setPendingFilters(filters); setDrawerOpen(true); }}
            filterCount={filterCount}
            onClearFilters={() => { setFilters(EMPTY_FILTERS); setPage(1); }}
          />

          {listQuery.isError ? (
            <ErrorState onRetry={() => listQuery.refetch()} />
          ) : listQuery.isLoading ? (
            <SkeletonBlock rows={8} />
          ) : rows.length === 0 ? (
            <EmptyState
              title="No contacts match"
              description="Try adjusting the search or filters, or add a new contact."
            />
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="w-10 px-3 py-2">
                      <Checkbox checked={allSelected} onCheckedChange={toggleAll} aria-label="Select all" />
                    </th>
                    <SortHeader label="Contact" k="fullName" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                    <SortHeader label="Location" k="state" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                    <SortHeader label="Language" k="preferredLanguage" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                    <th className="px-3 py-2 text-left font-medium">Channel</th>
                    <SortHeader label="Status" k="status" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                    <SortHeader label="Updated" k="updatedAt" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <motion.tr
                      key={row.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.008 }}
                      className={cn("border-t hover:bg-muted/30", selected.includes(row.id) && "bg-primary/5")}
                    >
                      <td className="px-3 py-2">
                        <Checkbox
                          checked={selected.includes(row.id)}
                          onCheckedChange={() => toggleRow(row.id)}
                          aria-label={`Select ${row.fullName}`}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <Link to="/audience/$id" params={{ id: row.id }} className="flex items-center gap-2 group">
                          <AudienceAvatar name={row.fullName} src={row.avatarUrl} size="sm" />
                          <div className="min-w-0">
                            <p className="truncate font-medium text-foreground group-hover:text-primary">{row.fullName}</p>
                            <p className="truncate text-xs text-muted-foreground">{row.email}</p>
                          </div>
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground">
                        <p className="text-foreground">{row.city}</p>
                        <p className="text-xs">{row.state}</p>
                      </td>
                      <td className="px-3 py-2 uppercase text-xs font-medium">{row.preferredLanguage}</td>
                      <td className="px-3 py-2 capitalize">{row.preferredChannel}</td>
                      <td className="px-3 py-2"><StatusBadge status={row.status} /></td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {new Date(row.updatedAt).toLocaleDateString()}
                      </td>
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
                  {[10, 25, 50, 100].map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
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
        <Select onValueChange={(v) => bulkStatus(v as AudienceStatus)}>
          <SelectTrigger className="h-8 w-40"><SelectValue placeholder="Set status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="opted_out">Opted out</SelectItem>
          </SelectContent>
        </Select>
        <PermissionGuard anyOf={[PERMISSIONS.TAG_MANAGE]}>
          <Select onValueChange={(v) => { audienceService.bulkAssignTags(selected, [v]).then(() => { toast.success("Tag assigned"); qc.invalidateQueries({ queryKey: ["audience"] }); }); }}>
            <SelectTrigger className="h-8 w-36"><SelectValue placeholder="Assign tag" /></SelectTrigger>
            <SelectContent>
              {(tagsQuery.data ?? []).map((t) => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </PermissionGuard>
        <PermissionGuard anyOf={[PERMISSIONS.AUDIENCE_DELETE]}>
          <Button size="sm" variant="destructive" onClick={() => setDeleteOpen(true)} className="gap-2">
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
          options={[
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
            { value: "pending", label: "Pending" },
            { value: "opted_out", label: "Opted out" },
          ]}
          selected={pendingFilters.status}
          onChange={(v) => setPendingFilters((f) => ({ ...f, status: v as AudienceStatus[] }))}
        />
        <FilterGroup
          label="State"
          options={INDIAN_STATES.map((s) => ({ value: s, label: s }))}
          selected={pendingFilters.states}
          onChange={(v) => setPendingFilters((f) => ({ ...f, states: v }))}
        />
        <FilterGroup
          label="Language"
          options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))}
          selected={pendingFilters.languages}
          onChange={(v) => setPendingFilters((f) => ({ ...f, languages: v }))}
        />
        <FilterGroup
          label="Channel"
          options={COMMUNICATION_CHANNELS.map((c) => ({ value: c.key, label: c.label }))}
          selected={pendingFilters.channels}
          onChange={(v) => setPendingFilters((f) => ({ ...f, channels: v }))}
        />
      </FilterDrawer>

      <CsvUploadDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onImported={() => { qc.invalidateQueries({ queryKey: ["audience"] }); }}
      />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={`Archive ${selected.length} contact(s)?`}
        description="Archived contacts can be restored from the trash within 30 days."
        confirmLabel="Archive"
        destructive
        onConfirm={bulkDelete}
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
}: {
  label: string;
  options: { value: string; label: string }[];
  selected: string[];
  onChange: (v: string[]) => void;
}) {
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
                active ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-foreground",
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
