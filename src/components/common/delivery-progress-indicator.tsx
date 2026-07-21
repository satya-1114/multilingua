import { cn } from "@/lib/utils";
import type { DeliveryJob } from "@/types/delivery";

export function DeliveryProgressIndicator({ job, className }: { job: DeliveryJob; className?: string }) {
  const total = Math.max(1, job.totalRecipients);
  const delivered = Math.round((job.delivered / total) * 100);
  const failed = Math.round((job.failed / total) * 100);
  const opened = Math.round((job.opened / total) * 100);
  const clicked = Math.round((job.clicked / total) * 100);
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex h-2 overflow-hidden rounded-full bg-muted">
        <div className="bg-emerald-500 transition-all" style={{ width: `${delivered}%` }} />
        <div className="bg-rose-500 transition-all" style={{ width: `${failed}%` }} />
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
        <span>Delivered <span className="font-semibold text-foreground">{delivered}%</span></span>
        <span>Opened <span className="font-semibold text-foreground">{opened}%</span></span>
        <span>Clicked <span className="font-semibold text-foreground">{clicked}%</span></span>
        <span>Failed <span className="font-semibold text-foreground">{failed}%</span></span>
      </div>
    </div>
  );
}
