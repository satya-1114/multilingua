import { cn } from "@/lib/utils";
import type { AudienceStatus } from "@/types/audience";
import type { OrganizationStatus } from "@/types/organization";

type StatusValue = AudienceStatus | OrganizationStatus | string;

interface StatusBadgeProps {
  status: StatusValue;
  className?: string;
}

const TONE: Record<string, string> = {
  active: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-emerald-500/20",
  inactive: "bg-slate-500/10 text-slate-600 dark:text-slate-300 ring-slate-500/20",
  pending: "bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-amber-500/20",
  opted_out: "bg-rose-500/10 text-rose-700 dark:text-rose-400 ring-rose-500/20",
  suspended: "bg-rose-500/10 text-rose-700 dark:text-rose-400 ring-rose-500/20",
};

const LABEL: Record<string, string> = {
  active: "Active",
  inactive: "Inactive",
  pending: "Pending",
  opted_out: "Opted out",
  suspended: "Suspended",
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const key = String(status).toLowerCase();
  const tone = TONE[key] ?? TONE.inactive!;
  const label = LABEL[key] ?? status;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        tone,
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
