import { Badge } from "@/components/ui/badge";
import type { WorkflowStatus, WorkflowStepStatus } from "@/types/workflow";

const STATUS_TONE: Record<
  WorkflowStatus | WorkflowStepStatus,
  { label: string; className: string }
> = {
  pending: { label: "Pending", className: "bg-muted text-muted-foreground" },
  running: { label: "Running", className: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200" },
  completed: {
    label: "Completed",
    className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  },
  failed: {
    label: "Failed",
    className: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  },
  cancelled: {
    label: "Cancelled",
    className: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  },
  skipped: {
    label: "Skipped",
    className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  },
};

export function WorkflowStatusBadge({
  status,
}: {
  status: WorkflowStatus | WorkflowStepStatus;
}) {
  const meta = STATUS_TONE[status] ?? { label: status, className: "" };
  return (
    <Badge variant="secondary" className={meta.className}>
      {meta.label}
    </Badge>
  );
}
