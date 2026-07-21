import { Check, ChevronRight } from "lucide-react";
import { WORKFLOW_STEPS, CAMPAIGN_STATUS_META } from "@/constants/campaign";
import type { CampaignStatus } from "@/types/campaign";
import { cn } from "@/lib/utils";

interface Props {
  status: CampaignStatus;
  className?: string;
}

export function WorkflowStepper({ status, className }: Props) {
  const idx = WORKFLOW_STEPS.findIndex((s) => s.key === status);
  const currentIdx = idx === -1 ? WORKFLOW_STEPS.length - 1 : idx;

  return (
    <div className={cn("flex flex-wrap items-center gap-1 rounded-xl border bg-card p-2", className)}>
      {WORKFLOW_STEPS.map((step, i) => {
        const done = i < currentIdx;
        const current = i === currentIdx;
        return (
          <div key={step.key} className="flex items-center gap-1">
            <div
              className={cn(
                "flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
                done && "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
                current && "bg-primary text-primary-foreground shadow-sm",
                !done && !current && "text-muted-foreground",
              )}
            >
              <span
                className={cn(
                  "flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold ring-1",
                  done && "bg-emerald-500 text-white ring-emerald-500",
                  current && "bg-primary-foreground text-primary ring-primary-foreground",
                  !done && !current && "ring-border",
                )}
              >
                {done ? <Check className="h-3 w-3" /> : i + 1}
              </span>
              <span className="hidden sm:inline">{step.label}</span>
            </div>
            {i < WORKFLOW_STEPS.length - 1 && (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" />
            )}
          </div>
        );
      })}
      <div className="ml-auto hidden text-xs text-muted-foreground sm:block">
        {CAMPAIGN_STATUS_META[status].description}
      </div>
    </div>
  );
}
