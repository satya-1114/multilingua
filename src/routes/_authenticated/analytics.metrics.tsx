import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/common/empty-state";
import { Pagination } from "@/components/common/pagination";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { usePermissions } from "@/hooks/use-permissions";
import { PERMISSIONS } from "@/constants/rbac";
import { queryKeys } from "@/lib/queryKeys";
import { analyticsService } from "@/services/analytics.service";
import type { AnalyticsMetric, MetricScope } from "@/types/analytics";

export const Route = createFileRoute("/_authenticated/analytics/metrics")({
  head: () => ({
    meta: [
      { title: "Metrics — Analytics" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: MetricsPage,
});

const SCOPES: MetricScope[] = [
  "volunteer",
  "disaster",
  "public_resource",
  "translation",
  "organization",
  "platform",
];

function MetricsPage() {
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.ANALYTICS_VIEW);
  const canManage = hasPermission(PERMISSIONS.ANALYTICS_MANAGE);

  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [scope, setScope] = useState<string | undefined>();
  const qStr = useDebouncedValue(search, 300);

  const qc = useQueryClient();
  const filters = { q: qStr || undefined, metricScope: scope, page, pageSize };
  const q = useQuery({
    queryKey: queryKeys.analyticsMetrics.list(filters),
    queryFn: () => analyticsService.listMetrics(filters),
    enabled: canView,
  });

  const [deleteTarget, setDeleteTarget] = useState<AnalyticsMetric | null>(null);
  const delMut = useMutation({
    mutationFn: (id: string) => analyticsService.deleteMetric(id),
    onSuccess: () => {
      toast.success("Metric deleted");
      qc.invalidateQueries({ queryKey: queryKeys.analyticsMetrics.all });
      setDeleteTarget(null);
    },
    onError: (e: Error) => toast.error(e.message || "Delete failed"),
  });

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Analytics access required</AlertTitle>
        <AlertDescription>You do not have permission to view metrics.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="shadow-card">
        <CardContent className="flex flex-wrap items-end gap-2 p-4">
          <div className="min-w-[220px] flex-1 space-y-1">
            <Label className="text-xs">Search</Label>
            <Input
              placeholder="Search metric name…"
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
            />
          </div>
          <div className="min-w-[180px] space-y-1">
            <Label className="text-xs">Scope</Label>
            <Select
              value={scope ?? "__all"}
              onValueChange={(v) => {
                setPage(1);
                setScope(v === "__all" ? undefined : v);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="All scopes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">All scopes</SelectItem>
                {SCOPES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {canManage && <CreateMetricDialog />}
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardContent className="p-0">
          {q.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : q.isError ? (
            <Alert variant="destructive" className="m-4">
              <AlertTitle>Could not load metrics</AlertTitle>
              <AlertDescription>{(q.error as Error).message}</AlertDescription>
            </Alert>
          ) : (q.data?.items.length ?? 0) === 0 ? (
            <div className="p-6">
              <EmptyState title="No metrics" description="No data points match your filters." />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Scope</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                  <TableHead>Recorded at</TableHead>
                  {canManage && <TableHead className="w-16" />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {q.data!.items.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">{m.metricName}</TableCell>
                    <TableCell className="text-xs uppercase tracking-wide text-muted-foreground">
                      {m.metricScope}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {m.entityType ? `${m.entityType}` : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {Number(m.metricValue).toLocaleString()}
                      {m.metricUnit ? ` ${m.metricUnit}` : ""}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(m.recordedAt).toLocaleString()}
                    </TableCell>
                    {canManage && (
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeleteTarget(m)}
                          aria-label="Delete metric"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
        {q.data && q.data.total > 0 && (
          <div className="px-4 pb-3">
            <Pagination page={page} pageSize={pageSize} total={q.data.total} onPageChange={setPage} />
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete metric?"
        description={`Permanently delete ${deleteTarget?.metricName ?? ""}.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (deleteTarget) delMut.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
}

function CreateMetricDialog() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [scope, setScope] = useState<MetricScope>("platform");
  const [value, setValue] = useState<string>("0");

  const mut = useMutation({
    mutationFn: () =>
      analyticsService.createMetric({
        metricName: name.trim(),
        metricScope: scope,
        metricValue: Number(value),
        recordedAt: new Date().toISOString(),
      }),
    onSuccess: () => {
      toast.success("Metric recorded");
      qc.invalidateQueries({ queryKey: queryKeys.analyticsMetrics.all });
      setOpen(false);
      setName("");
      setValue("0");
    },
    onError: (e: Error) => toast.error(e.message || "Create failed"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="mr-1 h-4 w-4" /> Record metric
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record metric</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="volunteer.hours" />
          </div>
          <div className="space-y-1">
            <Label>Scope</Label>
            <Select value={scope} onValueChange={(v) => setScope(v as MetricScope)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCOPES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label>Value</Label>
            <Input type="number" value={value} onChange={(e) => setValue(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!name.trim() || mut.isPending} onClick={() => mut.mutate()}>
            {mut.isPending ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
