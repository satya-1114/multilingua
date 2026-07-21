import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search, Siren } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { SectionHeader } from "@/components/common/section-header";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { PermissionGuard } from "@/components/common/permission-guard";
import {
  DisasterSeverityBadge,
  DisasterStatusBadge,
  DisasterTypeBadge,
} from "@/components/common/disaster-badges";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { disasterService } from "@/services/disaster.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { PERMISSIONS } from "@/constants/rbac";
import {
  DISASTER_TYPES,
  DISASTER_SEVERITIES,
  DISASTER_STATUSES,
  type Disaster,
  type DisasterListQuery,
} from "@/types/disaster";

export const Route = createFileRoute("/_authenticated/disasters/")({
  head: () => ({
    meta: [
      { title: "Disasters — Multilingua" },
      { name: "description", content: "Operational disaster response center." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: DisastersPage,
});

const PAGE_SIZE = 20;

function DisastersPage() {
  const [search, setSearch] = useState("");
  const [type, setType] = useState<string>("all");
  const [severity, setSeverity] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");
  const [state, setStateFilter] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search, 300);
  const debouncedState = useDebouncedValue(state, 300);

  const query = useMemo<DisasterListQuery>(
    () => ({
      page,
      pageSize: PAGE_SIZE,
      search: debouncedSearch || undefined,
      disasterType: type !== "all" ? (type as DisasterListQuery["disasterType"]) : undefined,
      severity: severity !== "all" ? (severity as DisasterListQuery["severity"]) : undefined,
      status: status !== "all" ? (status as DisasterListQuery["status"]) : undefined,
      state: debouncedState || undefined,
      sortBy: "startedAt",
      sortDir: "desc",
    }),
    [debouncedSearch, type, severity, status, debouncedState, page],
  );

  const listQ = useQuery({
    queryKey: ["disasters", query],
    queryFn: () => disasterService.list(query),
  });

  const items: Disaster[] = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const columns: DataTableColumn<Disaster>[] = [
    {
      key: "title",
      header: "Title",
      render: (d) => (
        <div className="min-w-0">
          <Link
            to="/disasters/$id"
            params={{ id: d.id }}
            className="font-medium text-foreground hover:underline"
          >
            {d.title}
          </Link>
          {d.address && <p className="text-xs text-muted-foreground truncate">{d.address}</p>}
        </div>
      ),
    },
    { key: "disasterType", header: "Type", render: (d) => <DisasterTypeBadge type={d.disasterType} /> },
    { key: "severity", header: "Severity", render: (d) => <DisasterSeverityBadge severity={d.severity} /> },
    { key: "status", header: "Status", render: (d) => <DisasterStatusBadge status={d.status} /> },
    {
      key: "region",
      header: "Region",
      render: (d) => (
        <span className="text-sm text-muted-foreground">
          {[d.city, d.state].filter(Boolean).join(", ") || "—"}
        </span>
      ),
    },
    {
      key: "startedAt",
      header: "Started",
      render: (d) => (
        <span className="text-sm text-muted-foreground">
          {d.startedAt
            ? formatDistanceToNow(new Date(d.startedAt), { addSuffix: true })
            : "—"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Disaster management"
        description="Coordinate emergency response, assignments and situational updates."
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.DISASTER_MANAGE]}>
            <Button asChild size="sm" className="gap-1.5">
              <Link to="/disasters/new"><Plus className="h-4 w-4" /> New disaster</Link>
            </Button>
          </PermissionGuard>
        }
      />

      <Card className="shadow-card">
        <CardContent className="flex flex-col gap-3 py-4 md:flex-row md:flex-wrap md:items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by title or address…"
              className="pl-9"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <Select value={type} onValueChange={(v) => { setType(v); setPage(1); }}>
            <SelectTrigger className="w-[170px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {DISASTER_TYPES.map((c) => (
                <SelectItem key={c} value={c} className="capitalize">
                  {c.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={severity} onValueChange={(v) => { setSeverity(v); setPage(1); }}>
            <SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any severity</SelectItem>
              {DISASTER_SEVERITIES.map((s) => (
                <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
            <SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any status</SelectItem>
              {DISASTER_STATUSES.map((s) => (
                <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            placeholder="State…"
            className="w-[160px]"
            value={state}
            onChange={(e) => { setStateFilter(e.target.value); setPage(1); }}
          />
        </CardContent>
      </Card>

      {listQ.isLoading ? (
        <SkeletonBlock rows={8} />
      ) : listQ.isError ? (
        <ErrorState
          title="Could not load disasters"
          description={(listQ.error as Error).message}
          onRetry={() => listQ.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Siren}
          title="No disasters yet"
          description="Create a disaster to coordinate emergency response and assignments."
        />
      ) : (
        <>
          <DataTable<Disaster> rows={items} columns={columns} rowKey={(d) => d.id} />
          {pageCount > 1 && (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Page {page} of {pageCount} · {total} total</span>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button size="sm" variant="outline" disabled={page >= pageCount} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
