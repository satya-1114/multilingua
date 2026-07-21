import { cn } from "@/lib/utils";

type ApprovalStatus = "pending" | "approved" | "rejected" | "sent_back" | "none";

const LABEL: Record<ApprovalStatus, string> = {
  pending: "Awaiting approval",
  approved: "Approved",
  rejected: "Rejected",
  sent_back: "Sent back",
  none: "Not submitted",
};

const TONE: Record<ApprovalStatus, string> = {
  pending: "bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-amber-500/20",
  approved: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-emerald-500/20",
  rejected: "bg-rose-500/10 text-rose-700 dark:text-rose-400 ring-rose-500/20",
  sent_back: "bg-sky-500/10 text-sky-700 dark:text-sky-400 ring-sky-500/20",
  none: "bg-slate-500/10 text-slate-600 dark:text-slate-300 ring-slate-500/20",
};

interface Props {
  status: ApprovalStatus;
  className?: string;
}

export function ApprovalBadge({ status, className }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        TONE[status],
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {LABEL[status]}
    </span>
  );
}
