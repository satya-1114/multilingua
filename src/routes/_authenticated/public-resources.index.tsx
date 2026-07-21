import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Globe, Plus, Search } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { SectionHeader } from "@/components/common/section-header";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { publicAccessService } from "@/services/public-access.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { PERMISSIONS } from "@/constants/rbac";
import {
  RESOURCE_TYPES,
  VISIBILITIES,
  type PublicResource,
  type PublicResourceListQuery,
  type ResourceType,
  type Visibility,
} from "@/types/public-access";

export const Route = createFileRoute("/_authenticated/public-resources/")({
  head: () => ({
    meta: [
      { title: "Public information — Multilingua" },
      {
        name: "description",
        content: "Manage publicly shareable resources, QR codes, and view analytics.",
      },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: PublicResourcesPage,
});

const PAGE_SIZE = 20;

function PublicResourcesPage() {
  const [search, setSearch] = useState("");
  const [type, setType] = useState<string>("all");
  const [visibility, setVisibility] = useState<string>("all");
  const [activeOnly, setActiveOnly] = useState<boolean>(false);
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useMemo<PublicResourceListQuery>(
    () => ({
      page,
      pageSize: PAGE_SIZE,
      search: debouncedSearch || undefined,
      resourceType: type !== "all" ? (type as ResourceType) : undefined,
      visibility: visibility !== "all" ? (visibility as Visibility) : undefined,
      activeOnly: activeOnly || undefined,
      sortBy: "createdAt",
      sortDir: "desc",
    }),
    [debouncedSearch, type, visibility, activeOnly, page],
  );

  const listQ = useQuery({
    queryKey: ["public-resources", query],
    queryFn: () => publicAccessService.list(query),
  });

  const items: PublicResource[] = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const columns: DataTableColumn<PublicResource>[] = [
    {
      key: "title",
      header: "Title",
      render: (r) => (
        <div className="min-w-0">
          <Link
            to="/public-resources/$id"
            params={{ id: r.id }}
            className="font-medium text-foreground hover:underline"
          >
            {r.title}
          </Link>
          <p className="text-xs text-muted-foreground truncate">/{r.slug}</p>
        </div>
      ),
    },
    {
      key: "resourceType",
      header: "Type",
      render: (r) => (
        <Badge variant="secondary" className="capitalize">
          {r.resourceType.replace(/_/g, " ")}
        </Badge>
      ),
    },
    {
      key: "visibility",
      header: "Visibility",
      render: (r) => <VisibilityBadge visibility={r.visibility} />,
    },
    {
      key: "qrToken",
      header: "QR",
      render: (r) =>
        r.qrToken ? (
          <Badge variant="outline" className="font-mono text-xs">
            {r.qrToken.slice(0, 8)}…
          </Badge>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        ),
    },
    {
      key: "createdAt",
      header: "Created",
      render: (r) => (
        <span className="text-sm text-muted-foreground">
          {r.createdAt
            ? formatDistanceToNow(new Date(r.createdAt), { addSuffix: true })
            : "—"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Public information & QR"
        description="Publish shareable resources, manage QR metadata, and monitor anonymous views."
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.PUBLIC_MANAGE]}>
            <Button asChild size="sm" className="gap-1.5">
              <Link to="/public-resources/new">
                <Plus className="h-4 w-4" /> New resource
              </Link>
            </Button>
          </PermissionGuard>
        }
      />

      <Card className="shadow-card">
        <CardContent className="flex flex-col gap-3 py-4 md:flex-row md:flex-wrap md:items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by title or slug…"
              className="pl-9"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <Select value={type} onValueChange={(v) => { setType(v); setPage(1); }}>
            <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {RESOURCE_TYPES.map((t) => (
                <SelectItem key={t} value={t} className="capitalize">
                  {t.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={visibility}
            onValueChange={(v) => { setVisibility(v); setPage(1); }}
          >
            <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any visibility</SelectItem>
              {VISIBILITIES.map((v) => (
                <SelectItem key={v} value={v} className="capitalize">{v}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-input"
              checked={activeOnly}
              onChange={(e) => { setActiveOnly(e.target.checked); setPage(1); }}
            />
            Active only
          </label>
        </CardContent>
      </Card>

      {listQ.isLoading ? (
        <SkeletonBlock rows={8} />
      ) : listQ.isError ? (
        <ErrorState
          title="Could not load public resources"
          description={(listQ.error as Error).message}
          onRetry={() => listQ.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Globe}
          title="No public resources yet"
          description="Create a public resource to share information via slug or QR code."
        />
      ) : (
        <>
          <DataTable<PublicResource> rows={items} columns={columns} rowKey={(r) => r.id} />
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

function VisibilityBadge({ visibility }: { visibility: Visibility }) {
  const styles: Record<Visibility, string> = {
    public: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
    unlisted: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200",
    private: "bg-muted text-muted-foreground",
    expired: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200",
    disabled: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200",
  };
  return (
    <Badge variant="outline" className={`capitalize ${styles[visibility]}`}>
      {visibility}
    </Badge>
  );
}
