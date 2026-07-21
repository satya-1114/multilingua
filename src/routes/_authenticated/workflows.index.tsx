import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Play,
  Percent,
  Repeat,
  Timer,
  ServerCog,
  Workflow as WorkflowIcon,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/empty-state";
import { WorkflowStatusBadge } from "@/components/workflows/workflow-status-badge";
import { usePermissions } from "@/hooks/use-permissions";
import { PERMISSIONS } from "@/constants/rbac";
import { queryKeys } from "@/lib/queryKeys";
import { workflowEngineService } from "@/services/workflow-engine.service";

export const Route = createFileRoute("/_authenticated/workflows/")({
  component: WorkflowDashboardPage,
});

function WorkflowDashboardPage() {
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.WORKFLOW_VIEW);
  const canManage = hasPermission(PERMISSIONS.WORKFLOW_MANAGE);
  const q = useQuery({
    queryKey: queryKeys.workflow.dashboard(),
    queryFn: () => workflowEngineService.dashboard(),
    enabled: canView,
  });

  const stats = useQuery({
    queryKey: queryKeys.workflow.runtimeStatistics(),
    queryFn: () => workflowEngineService.runtimeStatistics(),
    enabled: canView && canManage,
  });
  const health = useQuery({
    queryKey: queryKeys.workflow.runtimeHealth(),
    queryFn: () => workflowEngineService.runtimeHealth(),
    enabled: canView && canManage,
    refetchInterval: 30_000,
  });
  const observability = useQuery({
    queryKey: queryKeys.workflow.observabilityMetrics(),
    queryFn: () => workflowEngineService.observabilityMetrics(),
    enabled: canView && canManage,
    refetchInterval: 30_000,
  });

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Workflow access required</AlertTitle>
        <AlertDescription>You do not have permission to view workflows.</AlertDescription>
      </Alert>
    );
  }

  const d = q.data;
  const kpis = [
    { label: "Total workflows", value: d?.totalWorkflows ?? 0, icon: WorkflowIcon },
    { label: "Enabled", value: d?.enabledWorkflows ?? 0, icon: CheckCircle2 },
    { label: "Running executions", value: d?.runningExecutions ?? 0, icon: Play },
    { label: "Failed executions", value: d?.failedExecutions ?? 0, icon: AlertTriangle },
  ];

  const overview = stats.data?.overview;
  const runtimeKpis = [
    {
      label: "Success rate",
      value: overview ? `${Math.round(overview.successRate * 100)}%` : "—",
      icon: Percent,
    },
    {
      label: "Retries",
      value: overview ? overview.totalRetries.toLocaleString() : "—",
      icon: Repeat,
    },
    {
      label: "Avg runtime",
      value: overview ? `${overview.avgDurationSeconds.toFixed(2)}s` : "—",
      icon: Timer,
    },
    {
      label: "Runtime health",
      value: health.data?.status ?? "—",
      icon: ServerCog,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        {kpis.map((k) =>
          q.isLoading ? (
            <Skeleton key={k.label} className="h-24" />
          ) : (
            <Card key={k.label} className="shadow-card">
              <CardContent className="flex items-center justify-between p-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {k.label}
                  </p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums">
                    {k.value.toLocaleString()}
                  </p>
                </div>
                <k.icon className="h-6 w-6 text-muted-foreground" />
              </CardContent>
            </Card>
          ),
        )}
      </div>

      {canManage ? (
        <div className="grid gap-3 md:grid-cols-4">
          {runtimeKpis.map((k) =>
            stats.isLoading || health.isLoading ? (
              <Skeleton key={k.label} className="h-24" />
            ) : (
              <Card key={k.label} className="shadow-card">
                <CardContent className="flex items-center justify-between p-4">
                  <div className="min-w-0">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      {k.label}
                    </p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums truncate">
                      {k.value}
                    </p>
                  </div>
                  <k.icon className="h-6 w-6 text-muted-foreground" />
                </CardContent>
              </Card>
            ),
          )}
        </div>
      ) : null}

      {canManage && health.data ? (
        <Card className="shadow-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <ServerCog className="h-4 w-4" /> Runtime health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-2 text-sm md:grid-cols-5">
              {Object.entries(health.data.checks).map(([name, c]) => (
                <li
                  key={name}
                  className="flex items-center justify-between rounded border px-3 py-2"
                >
                  <span className="capitalize">{name}</span>
                  <Badge
                    variant={c.status === "ok" ? "default" : "secondary"}
                    className="uppercase text-[10px]"
                  >
                    {c.status}
                  </Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      {canManage && observability.data ? (
        <Card className="shadow-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4" /> Observability
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-2 text-xs md:grid-cols-3">
              {Object.entries(observability.data).map(([k, v]) => (
                <li
                  key={k}
                  className="flex items-center justify-between rounded border px-3 py-2"
                >
                  <span className="text-muted-foreground truncate">{k}</span>
                  <span className="font-mono tabular-nums">
                    {typeof v === "number" || typeof v === "string"
                      ? String(v)
                      : JSON.stringify(v)}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}

      <Card className="shadow-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="h-4 w-4" /> Recent executions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {q.isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : q.isError ? (
            <Alert variant="destructive">
              <AlertTitle>Could not load dashboard</AlertTitle>
              <AlertDescription>{(q.error as Error).message}</AlertDescription>
            </Alert>
          ) : (d?.recentExecutions.length ?? 0) === 0 ? (
            <EmptyState
              title="No executions yet"
              description="Start a workflow to see execution history here."
            />
          ) : (
            <ul className="divide-y divide-border text-sm">
              {d!.recentExecutions.map((ex) => (
                <li key={ex.id} className="flex items-center justify-between gap-3 py-2">
                  <div className="min-w-0 flex-1">
                    <Link
                      to="/workflows/executions/$id"
                      params={{ id: ex.id }}
                      className="font-medium text-primary hover:underline"
                    >
                      {ex.triggerEvent ?? "manual"}
                    </Link>
                    <p className="text-xs text-muted-foreground truncate">
                      {new Date(ex.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <WorkflowStatusBadge status={ex.status} />
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
