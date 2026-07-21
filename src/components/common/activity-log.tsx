import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import { Activity, CheckCircle2, MessageSquare, Shield, Sparkles } from "lucide-react";

export interface ActivityEntry {
  id: string;
  at: string;
  actor: string;
  kind: "campaign" | "approval" | "ai" | "security" | "system";
  message: string;
}

const iconMap: Record<ActivityEntry["kind"], LucideIcon> = {
  campaign: MessageSquare,
  approval: CheckCircle2,
  ai: Sparkles,
  security: Shield,
  system: Activity,
};

export function ActivityLog({ entries }: { entries: ActivityEntry[] }) {
  return (
    <ul className="space-y-3">
      {entries.map((e) => {
        const Icon = iconMap[e.kind];
        return (
          <li key={e.id} className="flex gap-3">
            <div className={cn("mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary")}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm">
                <span className="font-medium">{e.actor}</span> <span className="text-muted-foreground">{e.message}</span>
              </p>
              <p className="text-[11px] text-muted-foreground">
                {formatDistanceToNow(new Date(e.at), { addSuffix: true })}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
