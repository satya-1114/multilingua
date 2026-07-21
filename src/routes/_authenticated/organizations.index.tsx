import { useMemo, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Plus, Building2, CheckCircle2, XCircle, PauseCircle } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { StatCard } from "@/components/common/stat-card";
import { OrganizationCard } from "@/components/common/organization-card";
import { DataTableToolbar } from "@/components/common/data-table-toolbar";
import { EmptyState } from "@/components/common/empty-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { organizationService } from "@/services/organization.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { ORGANIZATION_TYPES, PERMISSIONS, type OrganizationType } from "@/constants/rbac";
import type { OrganizationStatus } from "@/types/organization";

export const Route = createFileRoute("/_authenticated/organizations/")({
  head: () => ({ meta: [{ title: "Organizations — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: OrganizationsPage,
});

function OrganizationsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [type, setType] = useState<OrganizationType | "all">("all");
  const [status, setStatus] = useState<OrganizationStatus | "all">("all");
  const [sort, setSort] = useState<string>("updatedAt");
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      type: type === "all" ? undefined : [type],
      status: status === "all" ? undefined : [status],
      sortBy: sort,
      sortDir: "desc" as const,
      pageSize: 48,
    }),
    [debouncedSearch, type, status, sort],
  );

  const orgsQuery = useQuery({ queryKey: ["organizations", query], queryFn: () => organizationService.list(query) });
  const statsQuery = useQuery({ queryKey: ["organizations", "stats"], queryFn: () => organizationService.getStats() });

  const items = orgsQuery.data?.items ?? [];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Organizations"
        description="Manage tenant organizations and their workspaces."
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.ORG_CREATE]}>
            <Button size="sm" onClick={() => navigate({ to: "/organizations/new" })} className="gap-2">
              <Plus className="h-4 w-4" /> New organization
            </Button>
          </PermissionGuard>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total" value={String(statsQuery.data?.total ?? "—")} icon={Building2} index={0} />
        <StatCard label="Active" value={String(statsQuery.data?.active ?? "—")} icon={CheckCircle2} index={1} />
        <StatCard label="Inactive" value={String(statsQuery.data?.inactive ?? "—")} icon={XCircle} index={2} />
        <StatCard label="Suspended" value={String(statsQuery.data?.suspended ?? "—")} icon={PauseCircle} index={3} />
      </div>

      <DataTableToolbar
        search={search}
        onSearchChange={setSearch}
        placeholder="Search organizations…"
        actions={
          <>
            <Select value={type} onValueChange={(v) => setType(v as OrganizationType | "all")}>
              <SelectTrigger className="h-9 w-40"><SelectValue placeholder="Type" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                {ORGANIZATION_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={status} onValueChange={(v) => setStatus(v as OrganizationStatus | "all")}>
              <SelectTrigger className="h-9 w-36"><SelectValue placeholder="Status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sort} onValueChange={setSort}>
              <SelectTrigger className="h-9 w-40"><SelectValue placeholder="Sort by" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="updatedAt">Recently updated</SelectItem>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="audienceCount">Audience size</SelectItem>
              </SelectContent>
            </Select>
          </>
        }
      />

      {orgsQuery.isLoading ? (
        <SkeletonBlock rows={6} />
      ) : items.length === 0 ? (
        <EmptyState title="No organizations found" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((o) => <OrganizationCard key={o.id} organization={o} />)}
        </div>
      )}
    </div>
  );
}
