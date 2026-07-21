import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Ban,
  ChevronLeft,
  CircleCheck,
  CircleX,
  RotateCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/common/empty-state";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { WorkflowStatusBadge } from "@/components/workflows/workflow-status-badge";
import { usePermissions } from "@/hooks/use-permissions";
import { PERMISSIONS } from "@/constants/rbac";
import { queryKeys } from "@/lib/queryKeys";
import { workflowEngineService } from "@/services/workflow-engine.service";
import type { WorkflowExecutionStep } from "@/types/workflow";

export const Route = createFileRoute("/_authenticated/workflows/executions/$id")({
  component: ExecutionDetailPage,
});

function ExecutionDetailPage() {
  const { id } = Route.useParams();
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.WORKFLOW_VIEW);
  const canExecute = hasPermission(PERMISSIONS.WORKFLOW_EXECUTE);

  const qc = useQueryClient();
  const ex = useQuery({
    queryKey: queryKeys.workflowExecutions.detail(id),
    queryFn: () => workflowEngineService.getExecution(id),
    enabled: canView,
  });
  const steps = useQuery({
    queryKey: queryKeys.workflowSteps.list(id, { pageSize: 200 }),
    queryFn: () => workflowEngineService.listSteps(id, { pageSize: 200 }),
    enabled: canView,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: queryKeys.workflowExecutions.detail(id) });
    qc.invalidateQueries({ queryKey: queryKeys.workflowSteps.all });
  };

  const completeMut = useMutation({
    mutationFn: () => workflowEngineService.completeExecution(id),
    onSuccess: () => {
      toast.success("Execution completed");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });
  const failMut = useMutation({
    mutationFn: (reason: string) => workflowEngineService.failExecution(id, reason),
    onSuccess: () => {
      toast.success("Execution marked failed");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });
  const cancelMut = useMutation({
    mutationFn: () => workflowEngineService.cancelExecution(id, "user_cancelled"),
    onSuccess: () => {
      toast.success("Execution cancelled");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });

  const retryMut = useMutation({
    mutationFn: (stepId: string) => workflowEngineService.retryStep(stepId),
    onSuccess: () => {
      toast.success("Step retried");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Retry failed"),
  });

  const [confirm, setConfirm] = useState<null | "complete" | "fail" | "cancel">(null);

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Access denied</AlertTitle>
        <AlertDescription>You cannot view this execution.</AlertDescription>
      </Alert>
    );
  }

  if (ex.isLoading) return <Skeleton className="h-40 w-full" />;
  if (ex.isError)
    return (
      <Alert variant="destructive">
        <AlertTitle>Load failed</AlertTitle>
        <AlertDescription>{(ex.error as Error).message}</AlertDescription>
      </Alert>
    );

  const e = ex.data!;
  const items: WorkflowExecutionStep[] = steps.data?.items ?? [];
  const terminal = ["completed", "failed", "cancelled"].includes(e.status);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <ChevronLeft className="h-3 w-3" />
        <Link to="/workflows/executions" className="hover:underline">
          Back to executions
        </Link>
      </div>

      <Card className="shadow-card">
        <CardHeader className="pb-2 flex flex-row items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              Execution <WorkflowStatusBadge status={e.status} />
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Workflow{" "}
              <Link
                to="/workflows/$id"
                params={{ id: e.workflowDefinitionId }}
                className="text-primary hover:underline"
              >
                {e.workflowDefinitionId.slice(0, 8)}
              </Link>{" "}
              · trigger {e.triggerEvent ?? "manual"} · started{" "}
              {e.startedAt ? new Date(e.startedAt).toLocaleString() : "—"}
            </p>
            {e.failureReason && (
              <p className="mt-2 text-xs text-red-600">Failure: {e.failureReason}</p>
            )}
          </div>
          {canExecute && !terminal && (
            <div className="flex gap-1">
              <Button size="sm" variant="outline" onClick={() => setConfirm("complete")}>
                <CircleCheck className="mr-1 h-4 w-4" /> Complete
              </Button>
              <Button size="sm" variant="outline" onClick={() => setConfirm("fail")}>
                <CircleX className="mr-1 h-4 w-4" /> Fail
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirm("cancel")}>
                <Ban className="mr-1 h-4 w-4" /> Cancel
              </Button>
            </div>
          )}
        </CardHeader>
      </Card>

      <Card className="shadow-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Steps ({items.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {steps.isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : items.length === 0 ? (
            <EmptyState
              title="No steps"
              description="This execution has no steps recorded yet."
            />
          ) : (
            <ol className="space-y-3">
              {items.map((s, idx) => (
                <li key={s.id} className="rounded-md border border-border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                        {idx + 1}
                      </span>
                      <WorkflowStatusBadge status={s.status} />
                      {s.retryCount > 0 && (
                        <Badge variant="secondary" className="gap-1">
                          <RotateCw className="h-3 w-3" /> retry {s.retryCount}
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        action {s.workflowActionId.slice(0, 8)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      {s.startedAt && <span>{new Date(s.startedAt).toLocaleString()}</span>}
                      {canExecute && s.status === "failed" && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => retryMut.mutate(s.id)}
                          disabled={retryMut.isPending}
                        >
                          <RotateCw className="mr-1 h-4 w-4" /> Retry
                        </Button>
                      )}
                    </div>
                  </div>
                  {(s.errorMessage || Object.keys(s.outputJson || {}).length > 0) && (
                    <>
                      <Separator className="my-2" />
                      {s.errorMessage && (
                        <pre className="whitespace-pre-wrap rounded bg-red-50 p-2 text-xs text-red-800 dark:bg-red-950/40 dark:text-red-200">
                          {s.errorMessage}
                        </pre>
                      )}
                      {Object.keys(s.outputJson || {}).length > 0 && (
                        <pre className="mt-2 max-h-40 overflow-auto rounded bg-muted p-2 text-xs">
                          {JSON.stringify(s.outputJson, null, 2)}
                        </pre>
                      )}
                    </>
                  )}
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirm === "complete"}
        onOpenChange={(o) => !o && setConfirm(null)}
        title="Mark execution completed?"
        description="This marks the execution as successfully completed."
        confirmLabel="Complete"
        onConfirm={() => {
          completeMut.mutate();
          setConfirm(null);
        }}
      />
      <ConfirmDialog
        open={confirm === "fail"}
        onOpenChange={(o) => !o && setConfirm(null)}
        title="Mark execution failed?"
        description="This marks the execution as failed."
        confirmLabel="Fail"
        destructive
        onConfirm={() => {
          failMut.mutate("manual_fail");
          setConfirm(null);
        }}
      />
      <ConfirmDialog
        open={confirm === "cancel"}
        onOpenChange={(o) => !o && setConfirm(null)}
        title="Cancel execution?"
        description="This cancels the running execution."
        confirmLabel="Cancel execution"
        destructive
        onConfirm={() => {
          cancelMut.mutate();
          setConfirm(null);
        }}
      />
    </div>
  );
}
