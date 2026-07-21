import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  Play,
  Plus,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/common/empty-state";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { WorkflowStatusBadge } from "@/components/workflows/workflow-status-badge";
import { usePermissions } from "@/hooks/use-permissions";
import { PERMISSIONS } from "@/constants/rbac";
import { queryKeys } from "@/lib/queryKeys";
import { workflowEngineService } from "@/services/workflow-engine.service";
import type { WorkflowAction, WorkflowTrigger } from "@/types/workflow";

export const Route = createFileRoute("/_authenticated/workflows/$id")({
  component: WorkflowDetailPage,
});

function WorkflowDetailPage() {
  const { id } = Route.useParams();
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.WORKFLOW_VIEW);
  const canExecute = hasPermission(PERMISSIONS.WORKFLOW_EXECUTE);

  const qc = useQueryClient();
  const wf = useQuery({
    queryKey: queryKeys.workflowDefinitions.detail(id),
    queryFn: () => workflowEngineService.getDefinition(id),
    enabled: canView,
  });

  const startMut = useMutation({
    mutationFn: () =>
      workflowEngineService.startExecution(id, { triggerEvent: "manual.run" }),
    onSuccess: () => {
      toast.success("Execution started");
      qc.invalidateQueries({ queryKey: queryKeys.workflowExecutions.all });
    },
    onError: (e: Error) => toast.error(e.message || "Start failed"),
  });

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Access denied</AlertTitle>
        <AlertDescription>You cannot view this workflow.</AlertDescription>
      </Alert>
    );
  }

  if (wf.isLoading) return <Skeleton className="h-40 w-full" />;
  if (wf.isError)
    return (
      <Alert variant="destructive">
        <AlertTitle>Load failed</AlertTitle>
        <AlertDescription>{(wf.error as Error).message}</AlertDescription>
      </Alert>
    );

  const def = wf.data!;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <ChevronLeft className="h-3 w-3" />
        <Link to="/workflows/definitions" className="hover:underline">
          Back to definitions
        </Link>
      </div>

      <Card className="shadow-card">
        <CardHeader className="pb-2 flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base">{def.name}</CardTitle>
            {def.description && (
              <p className="mt-1 text-sm text-muted-foreground">{def.description}</p>
            )}
            <div className="mt-2 flex items-center gap-2 text-xs">
              <Badge variant="secondary" className="uppercase">
                {def.triggerType}
              </Badge>
              <Badge variant={def.enabled ? "default" : "secondary"}>
                {def.enabled ? "Enabled" : "Disabled"}
              </Badge>
              <span className="text-muted-foreground">v{def.version}</span>
            </div>
          </div>
          {canExecute && (
            <Button
              size="sm"
              onClick={() => startMut.mutate()}
              disabled={!def.enabled || startMut.isPending}
            >
              <Play className="mr-1 h-4 w-4" /> Start execution
            </Button>
          )}
        </CardHeader>
      </Card>

      <Tabs defaultValue="actions">
        <TabsList>
          <TabsTrigger value="actions">Actions</TabsTrigger>
          <TabsTrigger value="triggers">Triggers</TabsTrigger>
          <TabsTrigger value="executions">Executions</TabsTrigger>
        </TabsList>
        <TabsContent value="actions" className="mt-3">
          <ActionsPanel workflowId={id} />
        </TabsContent>
        <TabsContent value="triggers" className="mt-3">
          <TriggersPanel workflowId={id} />
        </TabsContent>
        <TabsContent value="executions" className="mt-3">
          <ExecutionsPanel workflowId={id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ─── Actions ─────────────────────────────────────────────────────────
function ActionsPanel({ workflowId }: { workflowId: string }) {
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission(PERMISSIONS.WORKFLOW_CREATE);
  const canUpdate = hasPermission(PERMISSIONS.WORKFLOW_UPDATE);
  const canManage = hasPermission(PERMISSIONS.WORKFLOW_MANAGE);

  const qc = useQueryClient();
  const q = useQuery({
    queryKey: queryKeys.workflowActions.list(workflowId),
    queryFn: () => workflowEngineService.listActions(workflowId),
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: queryKeys.workflowActions.list(workflowId) });

  const reorderMut = useMutation({
    mutationFn: (orderedIds: string[]) =>
      workflowEngineService.reorderActions(workflowId, orderedIds),
    onSuccess: () => {
      toast.success("Actions reordered");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Reorder failed"),
  });

  const toggleMut = useMutation({
    mutationFn: (a: WorkflowAction) =>
      workflowEngineService.updateAction(a.id, { enabled: !a.enabled }),
    onSuccess: () => invalidate(),
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });

  const [deleteTarget, setDeleteTarget] = useState<WorkflowAction | null>(null);
  const delMut = useMutation({
    mutationFn: (id: string) => workflowEngineService.deleteAction(id),
    onSuccess: () => {
      toast.success("Action deleted");
      invalidate();
      setDeleteTarget(null);
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });

  const items = q.data ?? [];
  const move = (idx: number, dir: -1 | 1) => {
    const next = idx + dir;
    if (next < 0 || next >= items.length) return;
    const ordered = items.map((a) => a.id);
    [ordered[idx], ordered[next]] = [ordered[next], ordered[idx]];
    reorderMut.mutate(ordered);
  };

  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm">Actions</CardTitle>
        {canCreate && <CreateActionDialog workflowId={workflowId} />}
      </CardHeader>
      <CardContent>
        {q.isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : q.isError ? (
          <Alert variant="destructive">
            <AlertDescription>{(q.error as Error).message}</AlertDescription>
          </Alert>
        ) : items.length === 0 ? (
          <EmptyState
            title="No actions"
            description="Add the first step to describe what this workflow does."
          />
        ) : (
          <ol className="space-y-2">
            {items.map((a, idx) => (
              <li
                key={a.id}
                className="flex items-center gap-2 rounded-md border border-border p-2"
              >
                <span className="w-8 text-center text-xs font-semibold tabular-nums">
                  #{a.sequence}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium">{a.actionType}</div>
                  <div className="text-xs text-muted-foreground truncate">
                    {Object.keys(a.configurationJson || {}).length > 0
                      ? JSON.stringify(a.configurationJson)
                      : "No configuration"}
                  </div>
                </div>
                <Badge variant={a.enabled ? "default" : "secondary"}>
                  {a.enabled ? "On" : "Off"}
                </Badge>
                {canUpdate && (
                  <>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label="Move up"
                      onClick={() => move(idx, -1)}
                      disabled={idx === 0 || reorderMut.isPending}
                    >
                      <ArrowUp className="h-4 w-4" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label="Move down"
                      onClick={() => move(idx, 1)}
                      disabled={idx === items.length - 1 || reorderMut.isPending}
                    >
                      <ArrowDown className="h-4 w-4" />
                    </Button>
                    <Switch
                      checked={a.enabled}
                      onCheckedChange={() => toggleMut.mutate(a)}
                      aria-label="Toggle action"
                    />
                  </>
                )}
                {canManage && (
                  <Button
                    size="icon"
                    variant="ghost"
                    aria-label="Delete action"
                    onClick={() => setDeleteTarget(a)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </li>
            ))}
          </ol>
        )}
      </CardContent>
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete action?"
        description="This will remove the step from the workflow."
        confirmLabel="Delete"
        destructive
        onConfirm={() => { if (deleteTarget) delMut.mutate(deleteTarget.id); }}
      />
    </Card>
  );
}

function CreateActionDialog({ workflowId }: { workflowId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [actionType, setActionType] = useState("notify");
  const [sequence, setSequence] = useState<string>("");
  const [configuration, setConfiguration] = useState("{}");
  const [enabled, setEnabled] = useState(true);

  const mut = useMutation({
    mutationFn: () => {
      let cfg: Record<string, unknown> = {};
      try {
        cfg = configuration ? JSON.parse(configuration) : {};
      } catch {
        throw new Error("Configuration must be valid JSON");
      }
      return workflowEngineService.createAction(workflowId, {
        actionType: actionType.trim(),
        sequence: sequence ? Number(sequence) : undefined,
        configurationJson: cfg,
        enabled,
      });
    },
    onSuccess: () => {
      toast.success("Action added");
      qc.invalidateQueries({ queryKey: queryKeys.workflowActions.list(workflowId) });
      setOpen(false);
      setActionType("notify");
      setSequence("");
      setConfiguration("{}");
      setEnabled(true);
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Plus className="mr-1 h-4 w-4" /> Add action
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add action</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Action type</Label>
            <Input value={actionType} onChange={(e) => setActionType(e.target.value)} placeholder="notify.email" />
          </div>
          <div className="space-y-1">
            <Label>Sequence (optional)</Label>
            <Input
              type="number"
              value={sequence}
              onChange={(e) => setSequence(e.target.value)}
              placeholder="Auto-append if blank"
            />
          </div>
          <div className="space-y-1">
            <Label>Configuration (JSON)</Label>
            <Textarea
              value={configuration}
              onChange={(e) => setConfiguration(e.target.value)}
              rows={5}
              className="font-mono text-xs"
            />
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={enabled} onCheckedChange={setEnabled} id="new-action-enabled" />
            <Label htmlFor="new-action-enabled">Enabled</Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button
            disabled={!actionType.trim() || mut.isPending}
            onClick={() => mut.mutate()}
          >
            {mut.isPending ? "Saving…" : "Add"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Triggers ────────────────────────────────────────────────────────
function TriggersPanel({ workflowId }: { workflowId: string }) {
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission(PERMISSIONS.WORKFLOW_CREATE);
  const canManage = hasPermission(PERMISSIONS.WORKFLOW_MANAGE);

  const qc = useQueryClient();
  const q = useQuery({
    queryKey: queryKeys.workflowTriggers.list(workflowId),
    queryFn: () => workflowEngineService.listTriggers(workflowId),
  });
  const invalidate = () =>
    qc.invalidateQueries({ queryKey: queryKeys.workflowTriggers.list(workflowId) });

  const [deleteTarget, setDeleteTarget] = useState<WorkflowTrigger | null>(null);
  const delMut = useMutation({
    mutationFn: (id: string) => workflowEngineService.deleteTrigger(id),
    onSuccess: () => {
      toast.success("Trigger deleted");
      invalidate();
      setDeleteTarget(null);
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });

  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2 flex flex-row items-center justify-between">
        <CardTitle className="text-sm">Triggers</CardTitle>
        {canCreate && <CreateTriggerDialog workflowId={workflowId} />}
      </CardHeader>
      <CardContent>
        {q.isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : (q.data?.items.length ?? 0) === 0 ? (
          <EmptyState title="No triggers" description="Add a trigger to activate this workflow." />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Conditions</TableHead>
                {canManage && <TableHead className="w-16" />}
              </TableRow>
            </TableHeader>
            <TableBody>
              {q.data!.items.map((t) => (
                <TableRow key={t.id}>
                  <TableCell className="font-medium">{t.eventName}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {t.eventSource ?? "—"}
                  </TableCell>
                  <TableCell className="max-w-md truncate text-xs text-muted-foreground">
                    {Object.keys(t.conditionsJson || {}).length > 0
                      ? JSON.stringify(t.conditionsJson)
                      : "—"}
                  </TableCell>
                  {canManage && (
                    <TableCell>
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label="Delete trigger"
                        onClick={() => setDeleteTarget(t)}
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
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete trigger?"
        description="This will stop routing this event to the workflow."
        confirmLabel="Delete"
        destructive
        onConfirm={() => { if (deleteTarget) delMut.mutate(deleteTarget.id); }}
      />
    </Card>
  );
}

function CreateTriggerDialog({ workflowId }: { workflowId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [eventName, setEventName] = useState("");
  const [eventSource, setEventSource] = useState("");
  const [conditions, setConditions] = useState("{}");

  const mut = useMutation({
    mutationFn: () => {
      let cond: Record<string, unknown> = {};
      try {
        cond = conditions ? JSON.parse(conditions) : {};
      } catch {
        throw new Error("Conditions must be valid JSON");
      }
      return workflowEngineService.createTrigger(workflowId, {
        eventName: eventName.trim(),
        eventSource: eventSource.trim() || null,
        conditionsJson: cond,
      });
    },
    onSuccess: () => {
      toast.success("Trigger created");
      qc.invalidateQueries({ queryKey: queryKeys.workflowTriggers.list(workflowId) });
      setOpen(false);
      setEventName("");
      setEventSource("");
      setConditions("{}");
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Plus className="mr-1 h-4 w-4" /> Add trigger
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add trigger</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Event name</Label>
            <Input value={eventName} onChange={(e) => setEventName(e.target.value)} placeholder="volunteer.created" />
          </div>
          <div className="space-y-1">
            <Label>Event source (optional)</Label>
            <Input value={eventSource} onChange={(e) => setEventSource(e.target.value)} placeholder="volunteer_module" />
          </div>
          <div className="space-y-1">
            <Label>Conditions (JSON)</Label>
            <Textarea
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
              rows={4}
              className="font-mono text-xs"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!eventName.trim() || mut.isPending} onClick={() => mut.mutate()}>
            {mut.isPending ? "Saving…" : "Add"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Executions (inline) ─────────────────────────────────────────────
function ExecutionsPanel({ workflowId }: { workflowId: string }) {
  const q = useQuery({
    queryKey: queryKeys.workflowExecutions.list(workflowId, { pageSize: 25 }),
    queryFn: () => workflowEngineService.listExecutions(workflowId, { pageSize: 25 }),
  });

  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Recent executions</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {q.isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : (q.data?.items.length ?? 0) === 0 ? (
          <div className="p-6">
            <EmptyState title="No executions" description="Trigger this workflow to see runs." />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Trigger</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Completed</TableHead>
                <TableHead className="w-24 text-right" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {q.data!.items.map((ex) => (
                <TableRow key={ex.id}>
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
    </Card>
  );
}
