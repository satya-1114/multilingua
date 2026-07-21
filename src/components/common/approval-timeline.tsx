import { Check, X, RotateCcw, Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import type { CampaignApprovalEntry } from "@/types/campaign";
import { cn } from "@/lib/utils";

const ICON = {
  pending: Clock,
  approved: Check,
  rejected: X,
  sent_back: RotateCcw,
};

const TONE = {
  pending: "text-amber-600 bg-amber-500/10 ring-amber-500/20",
  approved: "text-emerald-600 bg-emerald-500/10 ring-emerald-500/20",
  rejected: "text-rose-600 bg-rose-500/10 ring-rose-500/20",
  sent_back: "text-sky-600 bg-sky-500/10 ring-sky-500/20",
};

const LABEL = {
  pending: "Submitted for approval",
  approved: "Approved",
  rejected: "Rejected",
  sent_back: "Sent back for revision",
};

interface Props {
  entries: CampaignApprovalEntry[];
  className?: string;
}

export function ApprovalTimeline({ entries, className }: Props) {
  if (entries.length === 0) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        No approval activity yet.
      </p>
    );
  }
  return (
    <ol className={cn("relative space-y-4 border-l border-border pl-4", className)}>
      {entries.map((e) => {
        const Icon = ICON[e.status];
        return (
          <li key={e.id} className="relative">
            <span
              className={cn(
                "absolute -left-[22px] top-0 flex h-8 w-8 items-center justify-center rounded-full ring-1 ring-inset",
                TONE[e.status],
              )}
            >
              <Icon className="h-4 w-4" />
            </span>
            <div className="rounded-lg border bg-card p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-foreground">{LABEL[e.status]}</p>
                  <p className="text-xs text-muted-foreground">
                    {e.actorName}
                    {e.actorRole ? ` · ${e.actorRole}` : ""}
                  </p>
                </div>
                <span className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(e.at), { addSuffix: true })}
                </span>
              </div>
              {e.comment && (
                <p className="mt-2 whitespace-pre-line text-sm text-muted-foreground">{e.comment}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
