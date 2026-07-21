import { useMemo } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { toast } from "sonner";
import { CheckCircle2, ClipboardList } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { StatusBadge } from "@/components/common/status-badge";
import { StatCard } from "@/components/common/stat-card";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { taskService } from "@/services/task.service";
import { PERMISSIONS } from "@/constants/rbac";
import type { TaskStatus, VolunteerTask } from "@/types/volunteer";

export const Route = createFileRoute("/_authenticated/my-tasks")({
  head: () => ({
    meta: [
      { title: "My Tasks — Multilingua" },
      { name: "description", content: "Your assigned volunteer tasks." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: MyTasksPage,
});

function MyTasksPage() {
  const qc = useQueryClient();
  const tasksQ = useQuery({
    queryKey: ["tasks", "mine"],
    queryFn: () => taskService.mine(),
  });

  const tasks = tasksQ.data ?? [];
  const grouped = useMemo(() => {
    return {
      pending: tasks.filter((t) => t.status === "pending"),
      upcoming: tasks.filter((t) => t.status === "accepted" || t.status === "in_progress"),
      completed: tasks.filter((t) => t.status === "completed"),
    };
  }, [tasks]);

  async function setStatus(task: VolunteerTask, status: TaskStatus) {
    try {
      await taskService.setStatus(task.id, status);
      toast.success("Task updated");
      qc.invalidateQueries({ queryKey: ["tasks", "mine"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update");
    }
  }

  return (
    <PermissionGuard anyOf={[PERMISSIONS.TASK_ACT, PERMISSIONS.TASK_VIEW]}>
      <div className="space-y-6">
        <SectionHeader title="My Tasks" description="Tasks assigned to you across campaigns." />

        {tasksQ.isLoading ? (
          <SkeletonBlock rows={6} />
        ) : tasksQ.isError ? (
          <ErrorState onRetry={() => tasksQ.refetch()} />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <StatCard label="Pending" value={String(grouped.pending.length)} icon={ClipboardList} index={0} />
              <StatCard label="Upcoming" value={String(grouped.upcoming.length)} icon={ClipboardList} index={1} />
              <StatCard label="Completed" value={String(grouped.completed.length)} icon={CheckCircle2} index={2} />
            </div>

            <TaskSection
              title="Pending acceptance"
              tasks={grouped.pending}
              onAccept={(t) => setStatus(t, "accepted")}
              onReject={(t) => setStatus(t, "rejected")}
            />
            <TaskSection
              title="Upcoming"
              tasks={grouped.upcoming}
              onStart={(t) => setStatus(t, "in_progress")}
              onComplete={(t) => setStatus(t, "completed")}
            />
            <TaskSection title="Completed" tasks={grouped.completed} readOnly />
          </>
        )}
      </div>
    </PermissionGuard>
  );
}

interface TaskSectionProps {
  title: string;
  tasks: VolunteerTask[];
  onAccept?: (t: VolunteerTask) => void;
  onReject?: (t: VolunteerTask) => void;
  onStart?: (t: VolunteerTask) => void;
  onComplete?: (t: VolunteerTask) => void;
  readOnly?: boolean;
}

function TaskSection({ title, tasks, onAccept, onReject, onStart, onComplete, readOnly }: TaskSectionProps) {
  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2"><CardTitle className="text-base">{title}</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {tasks.length === 0 ? (
          <EmptyState title="Nothing here" description="No tasks in this bucket." />
        ) : tasks.map((t) => (
          <div key={t.id} className="flex items-start justify-between gap-3 rounded-lg border border-border p-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <p className="truncate font-medium">{t.title}</p>
                <StatusBadge status={t.status} />
                <Badge variant="outline" className="capitalize">{t.priority}</Badge>
              </div>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{t.description}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {t.campaignName ? `Campaign: ${t.campaignName} · ` : ""}
                Assigned {format(new Date(t.assignedAt), "PP")}
                {t.dueAt ? ` · Due ${format(new Date(t.dueAt), "PP")}` : ""}
              </p>
            </div>
            {!readOnly && (
              <div className="flex shrink-0 items-center gap-1">
                {onAccept && <Button size="sm" onClick={() => onAccept(t)}>Accept</Button>}
                {onReject && <Button size="sm" variant="ghost" onClick={() => onReject(t)}>Reject</Button>}
                {onStart && t.status === "accepted" && <Button size="sm" onClick={() => onStart(t)}>Start</Button>}
                {onComplete && <Button size="sm" variant="ghost" className="gap-1" onClick={() => onComplete(t)}><CheckCircle2 className="h-4 w-4" /> Complete</Button>}
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
