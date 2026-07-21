import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Ban, CheckCircle2, PlayCircle, Plus, Workflow } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { PermissionGuard } from "@/components/common/permission-guard";
import {
  LocaleBadge,
  TranslationJobStatusBadge,
} from "@/components/translations/translation-badges";
import { JobRequestDialog } from "@/components/translations/job-request-dialog";
import { PERMISSIONS } from "@/constants/rbac";
import { translationService } from "@/services/translation.service";
import { queryKeys } from "@/lib/queryKeys";
import {
  TRANSLATION_JOB_STATUSES,
  type TranslationJob,
  type TranslationJobInput,
  type TranslationJobListQuery,
} from "@/types/translation";

export const Route = createFileRoute("/_authenticated/translations/jobs")({
  head: () => ({
    meta: [
      { title: "Translation jobs — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: JobsPage,
});

const PAGE_SIZE = 25;

function JobsPage() {
  const qc = useQueryClient();
  const [status, setStatus] = useState("all");
  const [locale, setLocale] = useState("all");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);

  const query = useMemo<TranslationJobListQuery>(
    () => ({
      page,
      pageSize: PAGE_SIZE,
      status: status !== "all" ? (status as TranslationJobListQuery["status"]) : undefined,
      targetLocale: locale !== "all" ? locale : undefined,
      sortBy: "createdAt",
      sortDir: "desc",
    }),
    [page, status, locale],
  );

  const listQ = useQuery({
    queryKey: queryKeys.translationJobs.list(query as unknown as Record<string, unknown>),
    queryFn: () => translationService.listJobs(query),
  });

  const localesQ = useQuery({
    queryKey: queryKeys.translationLocales.list(true),
    queryFn: () => translationService.listLocales(true),
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: queryKeys.translationJobs.all });

  const createMutation = useMutation({
    mutationFn: (payload: TranslationJobInput) => translationService.createJob(payload),
    onSuccess: () => {
      toast.success("Job requested");
      invalidate();
      setDialogOpen(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => translationService.startJob(id),
    onSuccess: () => { toast.success("Job started"); invalidate(); },
    onError: (err: Error) => toast.error(err.message),
  });
  const completeMutation = useMutation({
    mutationFn: (id: string) => translationService.completeJob(id),
    onSuccess: () => { toast.success("Job completed"); invalidate(); },
    onError: (err: Error) => toast.error(err.message),
  });
  const cancelMutation = useMutation({
    mutationFn: (id: string) => translationService.cancelJob(id),
    onSuccess: () => { toast.success("Job cancelled"); invalidate(); },
    onError: (err: Error) => toast.error(err.message),
  });

  const items = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const columns: DataTableColumn<TranslationJob>[] = [
    {
      key: "entity",
      header: "Entity",
      render: (j) => (
        <div className="min-w-0">
          <p className="text-sm font-medium capitalize">{j.entityType.replace(/_/g, " ")}</p>
          <p className="truncate text-xs text-muted-foreground font-mono">{j.entityId}</p>
        </div>
      ),
    },
    {
      key: "locales",
      header: "Locales",
      render: (j) => (
        <div className="flex items-center gap-1">
          <LocaleBadge locale={j.sourceLocale} />
          <span className="text-muted-foreground">→</span>
          <LocaleBadge locale={j.targetLocale} />
        </div>
      ),
    },
    { key: "status", header: "Status", render: (j) => <TranslationJobStatusBadge status={j.status} /> },
    { key: "provider", header: "Provider", render: (j) => <span className="text-xs">{j.provider ?? "—"}</span> },
    {
      key: "requested",
      header: "Requested",
      render: (j) => (
        <span className="text-xs text-muted-foreground">
          {j.requestedAt
            ? formatDistanceToNow(new Date(j.requestedAt), { addSuffix: true })
            : "—"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (j) => (
        <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_MANAGE_GLOSSARY, PERMISSIONS.JOB_MANAGE]}>
          <div className="flex justify-end gap-1">
            <Button
              size="sm"
              variant="ghost"
              disabled={j.status !== "pending" || startMutation.isPending}
              onClick={() => startMutation.mutate(j.id)}
              title="Start"
              className="gap-1.5"
            >
              <PlayCircle className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={j.status !== "processing" || completeMutation.isPending}
              onClick={() => completeMutation.mutate(j.id)}
              title="Complete"
              className="gap-1.5"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={
                j.status === "completed" ||
                j.status === "cancelled" ||
                cancelMutation.isPending
              }
              onClick={() => cancelMutation.mutate(j.id)}
              title="Cancel"
              className="gap-1.5"
            >
              <Ban className="h-3.5 w-3.5" />
            </Button>
          </div>
        </PermissionGuard>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <Card className="shadow-card">
        <CardContent className="flex flex-col gap-3 py-4 md:flex-row md:flex-wrap md:items-center">
          <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
            <SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any status</SelectItem>
              {TRANSLATION_JOB_STATUSES.map((s) => (
                <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={locale} onValueChange={(v) => { setLocale(v); setPage(1); }}>
            <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any target locale</SelectItem>
              {(localesQ.data ?? []).map((l) => (
                <SelectItem key={l.locale} value={l.locale}>
                  {l.locale} — {l.displayName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="md:ml-auto">
            <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_USE, PERMISSIONS.JOB_MANAGE]}>
              <Button size="sm" className="gap-1.5" onClick={() => setDialogOpen(true)}>
                <Plus className="h-4 w-4" /> Request job
              </Button>
            </PermissionGuard>
          </div>
        </CardContent>
      </Card>

      {listQ.isLoading ? (
        <SkeletonBlock rows={6} />
      ) : listQ.isError ? (
        <ErrorState
          title="Could not load jobs"
          description={(listQ.error as Error).message}
          onRetry={() => listQ.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Workflow}
          title="No translation jobs"
          description="Request a translation job to hand off work to a translator or provider."
        />
      ) : (
        <>
          <DataTable<TranslationJob> rows={items} columns={columns} rowKey={(j) => j.id} />
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

      <JobRequestDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        locales={localesQ.data ?? []}
        submitting={createMutation.isPending}
        onSubmit={(payload) => createMutation.mutateAsync(payload).then(() => undefined)}
      />
    </div>
  );
}
