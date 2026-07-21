import { cn } from "@/lib/utils";
import type { DeliveryStatus } from "@/types/delivery";

const TONES: Record<DeliveryStatus, string> = {
  queued: "bg-slate-500/10 text-slate-700 dark:text-slate-300 ring-slate-500/20",
  scheduled: "bg-blue-500/10 text-blue-700 dark:text-blue-300 ring-blue-500/20",
  processing: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 ring-indigo-500/20",
  sent: "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 ring-cyan-500/20",
  delivered: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 ring-emerald-500/20",
  opened: "bg-teal-500/10 text-teal-700 dark:text-teal-300 ring-teal-500/20",
  clicked: "bg-violet-500/10 text-violet-700 dark:text-violet-300 ring-violet-500/20",
  responded: "bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300 ring-fuchsia-500/20",
  failed: "bg-rose-500/10 text-rose-700 dark:text-rose-300 ring-rose-500/20",
  bounced: "bg-rose-500/10 text-rose-700 dark:text-rose-300 ring-rose-500/20",
  cancelled: "bg-zinc-500/10 text-zinc-700 dark:text-zinc-300 ring-zinc-500/20",
  retrying: "bg-amber-500/10 text-amber-700 dark:text-amber-300 ring-amber-500/20",
  paused: "bg-orange-500/10 text-orange-700 dark:text-orange-300 ring-orange-500/20",
};

const LABELS: Record<DeliveryStatus, string> = {
  queued: "Queued", scheduled: "Scheduled", processing: "Processing", sent: "Sent",
  delivered: "Delivered", opened: "Opened", clicked: "Clicked", responded: "Responded",
  failed: "Failed", bounced: "Bounced", cancelled: "Cancelled", retrying: "Retrying", paused: "Paused",
};

export function DeliveryStatusBadge({ status, className }: { status: DeliveryStatus; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", TONES[status], className)}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {LABELS[status]}
    </span>
  );
}
