import { cn } from "@/lib/utils";
import { CAMPAIGN_STATUS_META } from "@/constants/campaign";
import type { CampaignStatus } from "@/types/campaign";

const TONE: Record<string, string> = {
  muted: "bg-slate-500/10 text-slate-600 dark:text-slate-300 ring-slate-500/20",
  primary: "bg-primary/10 text-primary ring-primary/20",
  accent: "bg-sky-500/10 text-sky-700 dark:text-sky-400 ring-sky-500/20",
  warning: "bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-amber-500/20",
  success: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-emerald-500/20",
  danger: "bg-rose-500/10 text-rose-700 dark:text-rose-400 ring-rose-500/20",
};

interface Props {
  status: CampaignStatus;
  className?: string;
  showDot?: boolean;
}

export function CampaignStatusBadge({ status, className, showDot = true }: Props) {
  const meta = CAMPAIGN_STATUS_META[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        TONE[meta.tone],
        className,
      )}
    >
      {showDot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {meta.label}
    </span>
  );
}
