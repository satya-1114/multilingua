import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export interface TimelineItem {
  id: string;
  title: string;
  description?: string;
  at: string;
  icon: LucideIcon;
  tone?: "primary" | "accent" | "success" | "warning" | "muted";
}

interface TimelineProps {
  items: TimelineItem[];
  className?: string;
}

const TONES: Record<NonNullable<TimelineItem["tone"]>, string> = {
  primary: "bg-primary/10 text-primary",
  accent: "bg-violet-500/10 text-violet-600",
  success: "bg-emerald-500/10 text-emerald-600",
  warning: "bg-amber-500/10 text-amber-600",
  muted: "bg-muted text-muted-foreground",
};

export function Timeline({ items, className }: TimelineProps) {
  return (
    <ol className={cn("relative border-l border-border pl-6", className)}>
      {items.map((it) => {
        const Icon = it.icon;
        return (
          <li key={it.id} className="mb-5 last:mb-0">
            <span
              className={cn(
                "absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full ring-4 ring-background",
                TONES[it.tone ?? "primary"],
              )}
            >
              <Icon className="h-3 w-3" />
            </span>
            <p className="text-sm font-medium text-foreground">{it.title}</p>
            {it.description && <p className="mt-0.5 text-xs text-muted-foreground">{it.description}</p>}
            <p className="mt-1 text-[11px] text-muted-foreground">
              {formatDistanceToNow(new Date(it.at), { addSuffix: true })}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
