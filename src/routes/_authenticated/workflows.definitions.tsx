import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Play, Plus, Power, PowerOff, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
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
import { workflowEngineService } from "@/services/workflow-engine.service";
import {
  WORKFLOW_TRIGGER_TYPES,
  type WorkflowDefinition,
  type WorkflowTriggerType,
} from "@/types/workflow";

export const Route = createFileRoute("/_authenticated/workflows/definitions")({
  component: DefinitionsPage,
});

function DefinitionsPage() {
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.WORKFLOW_VIEW);
  const canCreate = hasPermission(PERMISSIONS.WORKFLOW_CREATE);
  const canUpdate = hasPermission(PERMISSIONS.WORKFLOW_UPDATE);
  const canManage = hasPermission(PERMISSIONS.WORKFLOW_MANAGE);
  const canExecute = hasPermission(PERMISSIONS.WORKFLOW_EXECUTE);

  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [search, setSearch] = useState("");
  const [triggerType, setTriggerType] = useState<WorkflowTriggerType | undefined>();
  const [enabled, setEnabled] = useState<string>("__all");
  const qStr = useDebouncedValue(search, 300);

  const filters = {
    q: qStr || undefined,
    triggerType,
    enabled: enabled === "__all" ? undefined : enabled === "true",
    page,
    pageSize,
  };
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: queryKeys.workflowDefinitions.list(filters),
    queryFn: () => workflowEngineService.listDefinitions(filters),
    enabled: canView,
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: queryKeys.workflowDefinitions.all });

  const enableMut = useMutation({
    mutationFn: (id: string) => workflowEngineService.enableDefinition(id),
    onSuccess: () => {
      toast.success("Workflow enabled");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });
  const disableMut = useMutation({
    mutationFn: (id: string) => workflowEngineService.disableDefinition(id),
    onSuccess: () => {
      toast.success("Workflow disabled");
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Failed"),
  });
  const startMut = useMutation({
    mutationFn: (id: string) =>
      workflowEngineService.startExecution(id, { triggerEvent: "manual.run" }),
    onSuccess: () => {
      toast.success("Execution started");
      qc.invalidateQueries({ queryKey: queryKeys.workflowExecutions.all });
      qc.invalidateQueries({ queryKey: queryKeys.workflow.all });
    },
    onError: (e: Error) => toast.error(e.message || "Start failed"),
  });

  const [deleteTarget, setDeleteTarget] = useState<WorkflowDefinition | null>(null);
  const [editTarget, setEditTarget] = useState<WorkflowDefinition | null>(null);
  const delMut = useMutation({
    mutationFn: (id: string) => workflowEngineService.deleteDefinition(id),
    onSuccess: () => {
      toast.success("Workflow deleted");
      invalidate();
      setDeleteTarget(null);
    },
    onError: (e: Error) => toast.error(e.message || "Delete failed"),
  });

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Workflow access required</AlertTitle>
        <AlertDescription>You do not have permission to view workflows.</AlertDescription>
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
              placeholder="Search workflow name…"
              value={search}
              onChange={(e) => {
                setPage(1);
                setSearch(e.target.value);
              }}
            />
          </div>
          <div className="min-w-[160px] space-y-1">
            <Label className="text-xs">Trigger type</Label>
            <Select
              value={triggerType ?? "__all"}
              onValueChange={(v) => {
                setPage(1);
                setTriggerType(v === "__all" ? undefined : (v as WorkflowTriggerType));
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">All triggers</SelectItem>
                {WORKFLOW_TRIGGER_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="min-w-[140px] space-y-1">
            <Label className="text-xs">Enabled</Label>
            <Select
              value={enabled}
              onValueChange={(v) => {
                setPage(1);
                setEnabled(v);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">All</SelectItem>
                <SelectItem value="true">Enabled</SelectItem>
                <SelectItem value="false">Disabled</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {canCreate && <CreateDefinitionDialog />}
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
              <AlertTitle>Could not load workflows</AlertTitle>
              <AlertDescription>{(q.error as Error).message}</AlertDescription>
            </Alert>
          ) : (q.data?.items.length ?? 0) === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No workflows"
                description="Create your first workflow to start automating."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="w-56 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {q.data!.items.map((w) => (
                  <TableRow key={w.id}>
                    <TableCell className="font-medium">
                      <Link
                        to="/workflows/$id"
                        params={{ id: w.id }}
                        className="text-primary hover:underline"
                      >
                        {w.name}
                      </Link>
                      {w.description && (
                        <div className="text-xs text-muted-foreground">
                          {w.description}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-xs uppercase tracking-wide">
                      {w.triggerType}
                    </TableCell>
                    <TableCell>
                      <Badge variant={w.enabled ? "default" : "secondary"}>
                        {w.enabled ? "Enabled" : "Disabled"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">v{w.version}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(w.updatedAt).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {canExecute && (
                          <Button
                            size="icon"
                            variant="ghost"
                            aria-label="Start execution"
                            title="Start execution"
                            onClick={() => startMut.mutate(w.id)}
                            disabled={!w.enabled || startMut.isPending}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                        )}
                        {canManage &&
                          (w.enabled ? (
                            <Button
                              size="icon"
                              variant="ghost"
                              aria-label="Disable"
                              title="Disable"
                              onClick={() => disableMut.mutate(w.id)}
                              disabled={disableMut.isPending}
                            >
                              <PowerOff className="h-4 w-4" />
                            </Button>
                          ) : (
                            <Button
                              size="icon"
                              variant="ghost"
                              aria-label="Enable"
                              title="Enable"
                              onClick={() => enableMut.mutate(w.id)}
                              disabled={enableMut.isPending}
                            >
                              <Power className="h-4 w-4" />
                            </Button>
                          ))}
                        {canUpdate && (
                          <Button
                            size="icon"
                            variant="ghost"
                            aria-label="Edit"
                            onClick={() => setEditTarget(w)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                        )}
                        {canManage && (
                          <Button
                            size="icon"
                            variant="ghost"
                            aria-label="Delete"
                            onClick={() => setDeleteTarget(w)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
        {q.data && q.data.total > 0 && (
          <div className="px-4 pb-3">
            <Pagination
              page={page}
              pageSize={pageSize}
              total={q.data.total}
              onPageChange={setPage}
            />
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete workflow?"
        description={`Permanently delete "${deleteTarget?.name ?? ""}" and all associated triggers, actions, and history.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => { if (deleteTarget) delMut.mutate(deleteTarget.id); }}
      />

      {editTarget && (
        <EditDefinitionDialog
          workflow={editTarget}
          open={!!editTarget}
          onOpenChange={(o) => !o && setEditTarget(null)}
        />
      )}
    </div>
  );
}

function CreateDefinitionDialog() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState<WorkflowTriggerType>("manual");
  const [enabled, setEnabled] = useState(true);

  const mut = useMutation({
    mutationFn: () =>
      workflowEngineService.createDefinition({
        name: name.trim(),
        description: description.trim() || null,
        triggerType,
        enabled,
      }),
    onSuccess: () => {
      toast.success("Workflow created");
      qc.invalidateQueries({ queryKey: queryKeys.workflowDefinitions.all });
      setOpen(false);
      setName("");
      setDescription("");
      setTriggerType("manual");
      setEnabled(true);
    },
    onError: (e: Error) => toast.error(e.message || "Create failed"),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="mr-1 h-4 w-4" /> New workflow
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create workflow</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Volunteer welcome" />
          </div>
          <div className="space-y-1">
            <Label>Description</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this workflow do?"
              rows={3}
            />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label>Trigger type</Label>
              <Select
                value={triggerType}
                onValueChange={(v) => setTriggerType(v as WorkflowTriggerType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WORKFLOW_TRIGGER_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2 pt-6">
              <Switch checked={enabled} onCheckedChange={setEnabled} id="wf-enabled" />
              <Label htmlFor="wf-enabled">Enabled</Label>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button disabled={!name.trim() || mut.isPending} onClick={() => mut.mutate()}>
            {mut.isPending ? "Saving…" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditDefinitionDialog({
  workflow,
  open,
  onOpenChange,
}: {
  workflow: WorkflowDefinition;
  open: boolean;
  onOpenChange: (o: boolean) => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState(workflow.name);
  const [description, setDescription] = useState(workflow.description ?? "");
  const [triggerType, setTriggerType] = useState<WorkflowTriggerType>(
    workflow.triggerType,
  );

  const mut = useMutation({
    mutationFn: () =>
      workflowEngineService.updateDefinition(workflow.id, {
        name: name.trim(),
        description: description.trim() || null,
        triggerType,
      }),
    onSuccess: () => {
      toast.success("Workflow updated");
      qc.invalidateQueries({ queryKey: queryKeys.workflowDefinitions.all });
      onOpenChange(false);
    },
    onError: (e: Error) => toast.error(e.message || "Update failed"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit workflow</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>Description</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          <div className="space-y-1">
            <Label>Trigger type</Label>
            <Select value={triggerType} onValueChange={(v) => setTriggerType(v as WorkflowTriggerType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {WORKFLOW_TRIGGER_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
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
