import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Play, Plus, Trash2, XCircle } from "lucide-react";
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
import type { AnalyticsReport, ReportStatus } from "@/types/analytics";

export const Route = createFileRoute("/_authenticated/analytics/jobs")({
  head: () => ({
    meta: [
      { title: "Report jobs — Analytics" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ReportJobsPage,
});

const STATUSES: ReportStatus[] = ["pending", "generating", "completed", "failed", "expired"];

const STATUS_TONE: Record<string, string> = {
  pending: "bg-slate-500/10 text-slate-600",
  generating: "bg-blue-500/10 text-blue-700",
  completed: "bg-emerald-500/10 text-emerald-700",
  failed: "bg-rose-500/10 text-rose-700",
  expired: "bg-amber-500/10 text-amber-700",
};

function ReportJobsPage() {
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.ANALYTICS_VIEW);
  const canManage = hasPermission(PERMISSIONS.ANALYTICS_MANAGE);

  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [status, setStatus] = useState<string | undefined>();
  const qc = useQueryClient();
  const filters = { status, page, pageSize };
  const q = useQuery({
    queryKey: queryKeys.analyticsReports.list(filters),
    queryFn: () => analyticsService.listReports(filters),
    enabled: canView,
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: queryKeys.analyticsReports.all });

  const [deleteTarget, setDeleteTarget] = useState<AnalyticsReport | null>(null);

  const startMut = useMutation({
    mutationFn: (id: string) => analyticsService.startReport(id),
    onSuccess: () => {
      toast.success("Report started");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Start failed"),
  });
  const expireMut = useMutation({
    mutationFn: (id: string) => analyticsService.expireReport(id),
    onSuccess: () => {
      toast.success("Report expired");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Expire failed"),
  });
  const delMut = useMutation({
    mutationFn: (id: string) => analyticsService.deleteReport(id),
    onSuccess: () => {
      toast.success("Report deleted");
      invalidate();
      setDeleteTarget(null);
    },
    onError: (e: Error) => toast.error(e.message || "Delete failed"),
  });

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Analytics access required</AlertTitle>
        <AlertDescription>You do not have permission to view report jobs.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="shadow-card">
        <CardContent className="flex flex-wrap items-end gap-2 p-4">
          <div className="min-w-[180px] space-y-1">
            <Label className="text-xs">Status</Label>
            <Select
              value={status ?? "__all"}
              onValueChange={(v) => {
                setPage(1);
                setStatus(v === "__all" ? undefined : v);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">All statuses</SelectItem>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {canManage && <RequestReportDialog />}
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
              <AlertTitle>Could not load reports</AlertTitle>
              <AlertDescription>{(q.error as Error).message}</AlertDescription>
            </Alert>
          ) : (q.data?.items.length ?? 0) === 0 ? (
            <div className="p-6">
              <EmptyState title="No report jobs" description="Request a report to get started." />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead>Expires</TableHead>
                  {canManage && <TableHead className="w-40" />}
                </TableRow>
              </TableHeader>
              <TableBody>
                {q.data!.items.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium">{r.reportName}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{r.reportType}</TableCell>
                    <TableCell>
                      <Badge className={STATUS_TONE[String(r.status)] ?? "bg-muted"}>
                        {r.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {r.generatedAt ? new Date(r.generatedAt).toLocaleString() : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {r.expiresAt ? new Date(r.expiresAt).toLocaleString() : "—"}
                    </TableCell>
                    {canManage && (
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          {r.status === "pending" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Start"
                              disabled={startMut.isPending}
                              onClick={() => startMut.mutate(r.id)}
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          {r.status === "completed" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Expire"
                              disabled={expireMut.isPending}
                              onClick={() => expireMut.mutate(r.id)}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Delete"
                            onClick={() => setDeleteTarget(r)}
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
        title="Delete report?"
        description="This removes the report job and any tracking metadata."
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (deleteTarget) delMut.mutate(deleteTarget.id);
        }}
      />
    </div>
  );
}

function RequestReportDialog() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("platform");

  const mut = useMutation({
    mutationFn: () =>
      analyticsService.requestReport({
        reportName: name.trim(),
        reportType: type,
      }),
    onSuccess: () => {
      toast.success("Report requested");
      qc.invalidateQueries({ queryKey: queryKeys.analyticsReports.all });
      setOpen(false);
      setName("");
    },
    onError: (e: Error) => toast.error(e.message || "Request failed"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="mr-1 h-4 w-4" /> Request report
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request report</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Weekly platform summary"
            />
          </div>
          <div className="space-y-1">
            <Label>Type</Label>
            <Input value={type} onChange={(e) => setType(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!name.trim() || mut.isPending} onClick={() => mut.mutate()}>
            {mut.isPending ? "Requesting…" : "Request"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
