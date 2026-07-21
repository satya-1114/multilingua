import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { format } from "date-fns";
import { SectionHeader } from "@/components/common/section-header";
import { DataTableToolbar } from "@/components/common/data-table-toolbar";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { EmptyState } from "@/components/common/empty-state";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { auditService } from "@/services/audit.service";
import { PERMISSIONS } from "@/constants/rbac";
import type { AuditAction, AuditModule } from "@/types/audit";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/audit-logs")({
  head: () => ({ meta: [{ title: "Audit logs — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: () => (
    <PermissionGuard
      anyOf={[PERMISSIONS.AUDIT_VIEW]}
      fallback={<EmptyState title="Access denied" description="You do not have permission to view audit logs." />}
    >
      <AuditLogsPage />
    </PermissionGuard>
  ),
});

const ACTION_TONE: Record<string, string> = {
  created: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  updated: "bg-primary/10 text-primary",
  deleted: "bg-rose-500/10 text-rose-700 dark:text-rose-400",
  imported: "bg-violet-500/10 text-violet-700 dark:text-violet-400",
  exported: "bg-amber-500/10 text-amber-700 dark:text-amber-400",
  assigned: "bg-sky-500/10 text-sky-700 dark:text-sky-400",
  unassigned: "bg-muted text-muted-foreground",
  restored: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
};

function AuditLogsPage() {
  const [search, setSearch] = useState("");
  const [action, setAction] = useState<AuditAction | "all">("all");
  const [module, setModule] = useState<AuditModule | "all">("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useMemo(
    () => ({
      search: debouncedSearch || undefined,
      action: action === "all" ? undefined : [action],
      module: module === "all" ? undefined : [module],
      page, pageSize,
    }),
    [debouncedSearch, action, module, page, pageSize],
  );

  const listQuery = useQuery({ queryKey: ["audit", query], queryFn: () => auditService.list(query) });
  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Audit logs"
        description="Immutable record of every create, update, delete, import, and export."
      />

      <Card className="shadow-card">
        <CardContent className="space-y-4 pt-6">
          <DataTableToolbar
            search={search}
            onSearchChange={(v) => { setSearch(v); setPage(1); }}
            placeholder="Search by actor, entity, module…"
            actions={
              <>
                <Select value={action} onValueChange={(v) => { setAction(v as AuditAction | "all"); setPage(1); }}>
                  <SelectTrigger className="h-9 w-36"><SelectValue placeholder="Action" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All actions</SelectItem>
                    {["created", "updated", "deleted", "imported", "exported", "assigned"].map((a) => (
                      <SelectItem key={a} value={a}>{a}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={module} onValueChange={(v) => { setModule(v as AuditModule | "all"); setPage(1); }}>
                  <SelectTrigger className="h-9 w-40"><SelectValue placeholder="Module" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All modules</SelectItem>
                    <SelectItem value="audience">Audience</SelectItem>
                    <SelectItem value="audience_group">Groups</SelectItem>
                    <SelectItem value="audience_tag">Tags</SelectItem>
                    <SelectItem value="organization">Organization</SelectItem>
                    <SelectItem value="user">User</SelectItem>
                  </SelectContent>
                </Select>
              </>
            }
          />

          {listQuery.isLoading ? (
            <SkeletonBlock rows={8} />
          ) : items.length === 0 ? (
            <EmptyState title="No audit entries" />
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Date & time</th>
                    <th className="px-3 py-2 text-left font-medium">Actor</th>
                    <th className="px-3 py-2 text-left font-medium">Action</th>
                    <th className="px-3 py-2 text-left font-medium">Module</th>
                    <th className="px-3 py-2 text-left font-medium">Entity</th>
                    <th className="px-3 py-2 text-left font-medium">IP</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((l) => (
                    <tr key={l.id} className="border-t hover:bg-muted/30">
                      <td className="px-3 py-2 text-xs">
                        <p>{format(new Date(l.createdAt), "MMM d, yyyy")}</p>
                        <p className="text-muted-foreground">{format(new Date(l.createdAt), "HH:mm:ss")}</p>
                      </td>
                      <td className="px-3 py-2">{l.actorName}</td>
                      <td className="px-3 py-2">
                        <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium capitalize", ACTION_TONE[l.action] ?? "bg-muted")}>
                          {l.action}
                        </span>
                      </td>
                      <td className="px-3 py-2 capitalize text-muted-foreground">{l.module.replace("_", " ")}</td>
                      <td className="px-3 py-2 truncate max-w-[200px]">{l.entityLabel ?? "—"}</td>
                      <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{l.ipAddress}</td>
                    </tr>
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
              <span>· {total.toLocaleString()} entries</span>
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
    </div>
  );
}
