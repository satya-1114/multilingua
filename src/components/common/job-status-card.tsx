import { CheckCircle2, Clock, Loader2, RotateCcw, X, XCircle } from "lucide-react";
import type { JobRecord } from "@/types/jobs";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

const STATUS_META = {
  queued: { icon: Clock, tone: "text-muted-foreground", label: "Queued" },
  running: { icon: Loader2, tone: "text-primary", label: "Running" },
  completed: { icon: CheckCircle2, tone: "text-success", label: "Completed" },
  failed: { icon: XCircle, tone: "text-destructive", label: "Failed" },
  cancelled: { icon: X, tone: "text-muted-foreground", label: "Cancelled" },
} as const;

interface JobStatusCardProps {
  job: JobRecord;
  onRetry?: (job: JobRecord) => void;
  onCancel?: (job: JobRecord) => void;
}

export function JobStatusCard({ job, onRetry, onCancel }: JobStatusCardProps) {
  const meta = STATUS_META[job.status];
  const Icon = meta.icon;
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Icon
            className={cn(
              "h-4 w-4 shrink-0",
              meta.tone,
              job.status === "running" && "animate-spin",
            )}
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-foreground">
              {job.title}
            </p>
            <p className="text-xs text-muted-foreground">
              {meta.label} · updated {formatDistanceToNow(new Date(job.updatedAt))} ago
              {job.processed !== undefined && job.total !== undefined && (
                <> · {job.processed.toLocaleString()} / {job.total.toLocaleString()}</>
              )}
            </p>
          </div>
          <div className="flex items-center gap-1">
            {onCancel && (job.status === "queued" || job.status === "running") && (
              <Button size="sm" variant="ghost" onClick={() => onCancel(job)}>
                Cancel
              </Button>
            )}
            {onRetry && job.status === "failed" && (
              <Button size="sm" variant="secondary" onClick={() => onRetry(job)}>
                <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Retry
              </Button>
            )}
          </div>
        </div>
        {job.status !== "completed" && job.status !== "cancelled" && (
          <div className="mt-3">
            <Progress value={job.progress} />
          </div>
        )}
        {job.errorMessage && (
          <p className="mt-3 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {job.errorMessage}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
