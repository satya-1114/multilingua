import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
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
import { WorkflowStatusBadge } from "@/components/workflows/workflow-status-badge";
import { usePermissions } from "@/hooks/use-permissions";
import { PERMISSIONS } from "@/constants/rbac";
import { queryKeys } from "@/lib/queryKeys";
import { workflowEngineService } from "@/services/workflow-engine.service";
import {
  WORKFLOW_STATUSES,
  type WorkflowDefinition,
  type WorkflowExecution,
  type WorkflowStatus,
} from "@/types/workflow";

export const Route = createFileRoute("/_authenticated/workflows/executions/")({
  component: ExecutionsIndexPage,
});

function ExecutionsIndexPage() {
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.WORKFLOW_VIEW);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [status, setStatus] = useState<WorkflowStatus | undefined>();

  const defs = useQuery({
    queryKey: queryKeys.workflowDefinitions.list({ pageSize: 50 }),
    queryFn: () => workflowEngineService.listDefinitions({ pageSize: 50 }),
    enabled: canView,
  });

  const workflows: WorkflowDefinition[] = defs.data?.items ?? [];

  const key = queryKeys.workflowExecutions.list("__all__", {
    status,
    page,
    pageSize,
  });
  const execs = useQuery({
    queryKey: key,
    enabled: canView && !defs.isLoading,
    queryFn: async () => {
      const results: WorkflowExecution[] = [];
      let total = 0;
      await Promise.all(
        workflows.map(async (w) => {
          try {
            const r = await workflowEngineService.listExecutions(w.id, {
              status,
              pageSize: 100,
            });
            total += r.total;
            results.push(...r.items);
          } catch {
            /* swallow per-workflow errors */
          }
        }),
      );
      results.sort(
        (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
      );
      const start = (page - 1) * pageSize;
      return { items: results.slice(start, start + pageSize), total, page, pageSize };
    },
  });

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Access denied</AlertTitle>
        <AlertDescription>You cannot view workflow executions.</AlertDescription>
      </Alert>
    );
  }

  const nameFor = (id: string) => workflows.find((w) => w.id === id)?.name ?? id;

  return (
    <div className="space-y-4">
      <Card className="shadow-card">
        <CardContent className="flex flex-wrap items-end gap-2 p-4">
          <div className="min-w-[160px] space-y-1">
            <Label className="text-xs">Status</Label>
            <Select
              value={status ?? "__all"}
              onValueChange={(v) => {
                setPage(1);
                setStatus(v === "__all" ? undefined : (v as WorkflowStatus));
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">All statuses</SelectItem>
                {WORKFLOW_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardContent className="p-0">
          {execs.isLoading || defs.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : execs.isError ? (
            <Alert variant="destructive" className="m-4">
              <AlertTitle>Load failed</AlertTitle>
              <AlertDescription>{(execs.error as Error).message}</AlertDescription>
            </Alert>
          ) : (execs.data?.items.length ?? 0) === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No executions"
                description="Run a workflow to populate history here."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Workflow</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead className="w-24 text-right" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {execs.data!.items.map((ex) => (
                  <TableRow key={ex.id}>
                    <TableCell className="font-medium">
                      <Link
                        to="/workflows/$id"
                        params={{ id: ex.workflowDefinitionId }}
                        className="text-primary hover:underline"
                      >
                        {nameFor(ex.workflowDefinitionId)}
                      </Link>
                    </TableCell>
                    <TableCell className="text-sm">{ex.triggerEvent ?? "manual"}</TableCell>
                    <TableCell><WorkflowStatusBadge status={ex.status} /></TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {ex.startedAt ? new Date(ex.startedAt).toLocaleString() : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {ex.completedAt ? new Date(ex.completedAt).toLocaleString() : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        to="/workflows/executions/$id"
                        params={{ id: ex.id }}
                        className="text-xs text-primary hover:underline"
                      >
                        View
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
        {execs.data && execs.data.total > 0 && (
          <div className="px-4 pb-3">
            <Pagination
              page={page}
              pageSize={pageSize}
              total={execs.data.total}
              onPageChange={setPage}
            />
          </div>
        )}
      </Card>
    </div>
  );
}
