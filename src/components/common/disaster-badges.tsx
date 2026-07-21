import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type {
  AssignmentStatus,
  DisasterSeverity,
  DisasterStatus,
  DisasterType,
} from "@/types/disaster";

const SEVERITY_STYLES: Record<DisasterSeverity, string> = {
  low: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200",
  critical: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
};

const STATUS_STYLES: Record<DisasterStatus, string> = {
  reported: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  verified: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200",
  active: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
  contained: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200",
  resolved: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
  closed: "bg-muted text-muted-foreground",
};

const ASSIGNMENT_STATUS_STYLES: Record<AssignmentStatus, string> = {
  assigned: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  accepted: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200",
  in_progress: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200",
  completed: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200",
  cancelled: "bg-muted text-muted-foreground",
};

export function DisasterSeverityBadge({ severity }: { severity: DisasterSeverity }) {
  return (
    <Badge variant="outline" className={cn("capitalize border-transparent", SEVERITY_STYLES[severity])}>
      {severity}
    </Badge>
  );
}

export function DisasterStatusBadge({ status }: { status: DisasterStatus }) {
  return (
    <Badge variant="outline" className={cn("capitalize border-transparent", STATUS_STYLES[status])}>
      {status}
    </Badge>
  );
}

export function DisasterTypeBadge({ type }: { type: DisasterType }) {
  return (
    <Badge variant="secondary" className="capitalize">
      {type.replace(/_/g, " ")}
    </Badge>
  );
}

export function AssignmentStatusBadge({ status }: { status: AssignmentStatus }) {
  return (
    <Badge
      variant="outline"
      className={cn("capitalize border-transparent", ASSIGNMENT_STATUS_STYLES[status])}
    >
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
