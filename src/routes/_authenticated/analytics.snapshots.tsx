import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, RefreshCcw, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
import { usePermissions } from "@/hooks/use-permissions";
import { PERMISSIONS } from "@/constants/rbac";
import { queryKeys } from "@/lib/queryKeys";
import { analyticsService } from "@/services/analytics.service";
import type { AnalyticsSnapshot, SnapshotType } from "@/types/analytics";

export const Route = createFileRoute("/_authenticated/analytics/snapshots")({
  head: () => ({
    meta: [
      { title: "Snapshots — Analytics" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: SnapshotsPage,
});

const TYPES: SnapshotType[] = ["daily", "weekly", "monthly", "custom"];

function SnapshotsPage() {
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.ANALYTICS_VIEW);
  const canManage = hasPermission(PERMISSIONS.ANALYTICS_MANAGE);

  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [type, setType] = useState<string | undefined>();

  const qc = useQueryClient();
  const filters = { snapshotType: type, page, pageSize };
  const q = useQuery({
    queryKey: queryKeys.analyticsSnapshots.list(filters),
    queryFn: () => analyticsService.listSnapshots(filters),
    enabled: canView,
  });

  const [deleteTarget, setDeleteTarget] = useState<AnalyticsSnapshot | null>(null);
  const invalidate = () =>
    qc.invalidateQueries({ queryKey: queryKeys.analyticsSnapshots.all });

  const delMut = useMutation({
    mutationFn: (id: string) => analyticsService.deleteSnapshot(id),
    onSuccess: () => {
      toast.success("Snapshot deleted");
      invalidate();
      setDeleteTarget(null);
    },
    onError: (e: Error) => toast.error(e.message || "Delete failed"),
  });
  const regenMut = useMutation({
    mutationFn: (id: string) => analyticsService.regenerateSnapshot(id),
    onSuccess: () => {
      toast.success("Snapshot regenerated");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Regenerate failed"),
  });

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Analytics access required</AlertTitle>
        <AlertDescription>You do not have permission to view snapshots.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="shadow-card">
        <CardContent className="flex flex-wrap items-end gap-2 p-4">
          <div className="min-w-[180px] space-y-1">
            <Label className="text-xs">Type</Label>
            <Select
              value={type ?? "__all"}
              onValueChange={(v) => {
                setPage(1);
                setType(v === "__all" ? undefined : v);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">All types</SelectItem>
                {TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {canManage && <CreateSnapshotDialog />}
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
              <AlertTitle>Could not load snapshots</AlertTitle>
              <AlertDescription>{(q.error as Error).message}</AlertDescription>
            </Alert>
          ) : (q.data?.items.length ?? 0) === 0 ? (
            <div className="p-6">
              <EmptyState title="No snapshots" description="No snapshots have been generated yet." />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Generated at</TableHead>
                  <TableHead>Metrics</TableHead>
                  {canManage && <TableHead className="w-32" />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {q.data!.items.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell>
                      <Badge variant="outline">{s.snapshotType}</Badge>
                    </TableCell>
                    <TableCell className="text-xs">
                      <Link
                        to="/analytics/snapshots/$id"
                        params={{ id: s.id }}
                        className="hover:underline"
                      >
                        {new Date(s.periodStart).toLocaleDateString()} →{" "}
                        {new Date(s.periodEnd).toLocaleDateString()}
                      </Link>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(s.generatedAt).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {Object.keys(s.metricsJson ?? {}).length} keys
                    </TableCell>
                    {canManage && (
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Regenerate"
                            disabled={regenMut.isPending}
                            onClick={() => regenMut.mutate(s.id)}
                          >
                            <RefreshCcw className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Delete"
                            onClick={() => setDeleteTarget(s)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
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
        title="Delete snapshot?"
        description="This permanently removes the aggregated snapshot."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (deleteTarget) delMut.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
}

function CreateSnapshotDialog() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<SnapshotType>("daily");
  const today = new Date().toISOString().slice(0, 10);
  const [start, setStart] = useState(today);
  const [end, setEnd] = useState(today);

  const mut = useMutation({
    mutationFn: () =>
      analyticsService.createSnapshot({
        snapshotType: type,
        periodStart: new Date(start).toISOString(),
        periodEnd: new Date(end).toISOString(),
      }),
    onSuccess: () => {
      toast.success("Snapshot created");
      qc.invalidateQueries({ queryKey: queryKeys.analyticsSnapshots.all });
      setOpen(false);
    },
    onError: (e: Error) => toast.error(e.message || "Create failed"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="mr-1 h-4 w-4" /> New snapshot
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create snapshot</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Type</Label>
            <Select value={type} onValueChange={(v) => setType(v as SnapshotType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label>Start</Label>
              <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>End</Label>
              <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={mut.isPending} onClick={() => mut.mutate()}>
            {mut.isPending ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
