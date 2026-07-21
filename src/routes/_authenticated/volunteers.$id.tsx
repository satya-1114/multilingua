import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ArrowLeft, Building2, CheckCircle2, Mail, MapPin, Pencil, Phone, Plus, Trash2, UserRoundCog } from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { StatusBadge } from "@/components/common/status-badge";
import { PermissionGuard } from "@/components/common/permission-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { TaskAssignDialog } from "@/components/common/task-assign-dialog";
import { TaskReassignDialog } from "@/components/common/task-reassign-dialog";
import { VolunteerFormDialog } from "@/components/common/volunteer-form-dialog";
import { OrganizationAssignDialog } from "@/components/common/organization-assign-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { volunteerService } from "@/services/volunteer.service";
import { taskService } from "@/services/task.service";
import { PERMISSIONS } from "@/constants/rbac";
import type { VolunteerTask } from "@/types/volunteer";

export const Route = createFileRoute("/_authenticated/volunteers/$id")({
  head: () => ({
    meta: [
      { title: "Volunteer profile — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: VolunteerDetailPage,
});

function initials(name: string) {
  return name
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function VolunteerDetailPage() {
  const { id } = Route.useParams();
  const qc = useQueryClient();
  const [assignOpen, setAssignOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<VolunteerTask | null>(null);
  const [reassignTask, setReassignTask] = useState<VolunteerTask | null>(null);
  const [cancelId, setCancelId] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [orgOpen, setOrgOpen] = useState(false);

  const volunteerQ = useQuery({
    queryKey: ["volunteer", id],
    queryFn: () => volunteerService.get(id),
  });

  const tasksQ = useQuery({
    queryKey: ["volunteer", id, "tasks"],
    queryFn: () => volunteerService.tasks(id),
  });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["volunteer", id] });
    qc.invalidateQueries({ queryKey: ["volunteer", id, "tasks"] });
  };

  async function handleComplete(task: VolunteerTask) {
    try {
      await taskService.setStatus(task.id, "completed");
      toast.success("Task marked completed");
      refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update task");
    }
  }

  async function handleCancel() {
    if (!cancelId) return;
    try {
      await taskService.cancel(cancelId);
      toast.success("Assignment cancelled");
      setCancelId(null);
      refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to cancel");
    }
  }

  if (volunteerQ.isLoading) return <SkeletonBlock rows={10} />;
  if (volunteerQ.isError || !volunteerQ.data) return <ErrorState onRetry={() => volunteerQ.refetch()} />;

  const v = volunteerQ.data;
  const tasks = tasksQ.data ?? [];
  const upcoming = tasks.filter((t) => t.status !== "completed" && t.status !== "cancelled" && t.status !== "rejected");
  const history = tasks.filter((t) => t.status === "completed" || t.status === "cancelled" || t.status === "rejected");

  return (
    <PermissionGuard anyOf={[PERMISSIONS.VOLUNTEER_VIEW]}>
      <div className="space-y-6">
        <div>
          <Button asChild variant="ghost" size="sm" className="gap-1">
            <Link to="/volunteers"><ArrowLeft className="h-4 w-4" /> Back to volunteers</Link>
          </Button>
        </div>

        <SectionHeader
          title={v.fullName}
          description="Volunteer profile, assigned campaigns, and task history."
          actions={
            <div className="flex items-center gap-2">
              <PermissionGuard anyOf={[PERMISSIONS.VOLUNTEER_MANAGE]}>
                <Button size="sm" variant="outline" className="gap-1" onClick={() => setEditOpen(true)}>
                  <Pencil className="h-4 w-4" /> Edit
                </Button>
                <Button size="sm" variant="outline" className="gap-1" onClick={() => setOrgOpen(true)}>
                  <Building2 className="h-4 w-4" /> Organization
                </Button>
              </PermissionGuard>
              <PermissionGuard anyOf={[PERMISSIONS.TASK_ASSIGN]}>
                <Button size="sm" className="gap-1" onClick={() => { setEditingTask(null); setAssignOpen(true); }}>
                  <Plus className="h-4 w-4" /> Assign task
                </Button>
              </PermissionGuard>
            </div>
          }
        />

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="shadow-card lg:col-span-1">
            <CardContent className="space-y-4 p-6">
              <div className="flex items-center gap-4">
                <Avatar className="h-16 w-16">
                  <AvatarImage src={v.avatarUrl ?? undefined} alt={v.fullName} />
                  <AvatarFallback>{initials(v.fullName)}</AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold">{v.fullName}</h2>
                  <StatusBadge status={v.status} />
                </div>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Mail className="h-4 w-4" /> {v.email}
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Phone className="h-4 w-4" /> {v.phone || "—"}
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <MapPin className="h-4 w-4" /> {v.currentLocation || "—"}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Languages</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {v.languages.length ? v.languages.map((l) => <Badge key={l} variant="secondary">{l}</Badge>) : <span className="text-sm text-muted-foreground">—</span>}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Skills</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {v.skills.length ? v.skills.map((s) => <Badge key={s} variant="secondary">{s}</Badge>) : <span className="text-sm text-muted-foreground">—</span>}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Availability</p>
                <p className="mt-1 text-sm">{v.availability || "—"}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 border-t pt-3">
                <div>
                  <p className="text-xs uppercase text-muted-foreground">Active tasks</p>
                  <p className="text-xl font-semibold">{v.activeTaskCount}</p>
                </div>
                <div>
                  <p className="text-xs uppercase text-muted-foreground">Completed</p>
                  <p className="text-xl font-semibold">{v.completedTaskCount}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4 lg:col-span-2">
            <Card className="shadow-card">
              <CardHeader className="pb-2"><CardTitle className="text-base">Assigned campaigns</CardTitle></CardHeader>
              <CardContent>
                {v.assignedCampaignIds.length === 0 ? (
                  <EmptyState title="No campaigns assigned" description="Assign a task to link this volunteer to a campaign." />
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {v.assignedCampaignIds.map((cid) => (
                      <Badge key={cid} variant="outline">{cid}</Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="shadow-card">
              <CardHeader className="pb-2"><CardTitle className="text-base">Current tasks</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {tasksQ.isLoading ? <SkeletonBlock rows={3} /> : upcoming.length === 0 ? (
                  <EmptyState title="No active tasks" description="This volunteer has no open assignments." />
                ) : upcoming.map((t) => (
                  <TaskRow
                    key={t.id}
                    task={t}
                    onEdit={() => { setEditingTask(t); setAssignOpen(true); }}
                    onComplete={() => handleComplete(t)}
                    onCancel={() => setCancelId(t.id)}
                    onReassign={() => setReassignTask(t)}
                  />
                ))}
              </CardContent>
            </Card>

            <Card className="shadow-card">
              <CardHeader className="pb-2"><CardTitle className="text-base">Task history</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {history.length === 0 ? (
                  <EmptyState title="No history yet" description="Completed and cancelled tasks appear here." />
                ) : history.map((t) => <TaskRow key={t.id} task={t} readOnly />)}
              </CardContent>
            </Card>
          </div>
        </div>

        <TaskAssignDialog
          open={assignOpen}
          onOpenChange={setAssignOpen}
          volunteerId={v.id}
          volunteerName={v.fullName}
          task={editingTask}
          onSaved={refresh}
        />

        <ConfirmDialog
          open={Boolean(cancelId)}
          onOpenChange={(o) => !o && setCancelId(null)}
          title="Cancel assignment?"
          description="The volunteer will be notified that this task has been cancelled."
          confirmLabel="Cancel task"
          onConfirm={handleCancel}
        />

        <VolunteerFormDialog
          open={editOpen}
          onOpenChange={setEditOpen}
          volunteer={v}
          onSaved={refresh}
        />

        <OrganizationAssignDialog
          open={orgOpen}
          onOpenChange={setOrgOpen}
          volunteer={v}
          onSaved={refresh}
        />

        {reassignTask && (
          <TaskReassignDialog
            open={Boolean(reassignTask)}
            onOpenChange={(o) => !o && setReassignTask(null)}
            task={reassignTask}
            onSaved={() => { setReassignTask(null); refresh(); }}
          />
        )}
      </div>
    </PermissionGuard>
  );
}

interface TaskRowProps {
  task: VolunteerTask;
  onEdit?: () => void;
  onComplete?: () => void;
  onCancel?: () => void;
  onReassign?: () => void;
  readOnly?: boolean;
}

function TaskRow({ task, onEdit, onComplete, onCancel, onReassign, readOnly }: TaskRowProps) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-border p-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium">{task.title}</p>
          <StatusBadge status={task.status} />
          <Badge variant="outline" className="capitalize">{task.priority}</Badge>
        </div>
        <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{task.description}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {task.campaignName ? `Campaign: ${task.campaignName} · ` : ""}
          Assigned {format(new Date(task.assignedAt), "PP")}
          {task.dueAt ? ` · Due ${format(new Date(task.dueAt), "PP")}` : ""}
        </p>
      </div>
      {!readOnly && (
        <PermissionGuard anyOf={[PERMISSIONS.TASK_MANAGE, PERMISSIONS.TASK_ASSIGN]}>
          <div className="flex shrink-0 items-center gap-1">
            {task.status !== "completed" && (
              <Button size="sm" variant="ghost" className="gap-1" onClick={onComplete}>
                <CheckCircle2 className="h-4 w-4" /> Complete
              </Button>
            )}
            {onReassign && (
              <Button size="sm" variant="ghost" className="gap-1" onClick={onReassign}>
                <UserRoundCog className="h-4 w-4" /> Reassign
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={onEdit}>Edit</Button>
            <Button size="sm" variant="ghost" className="text-destructive" onClick={onCancel}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </PermissionGuard>
      )}
    </div>
  );
}
