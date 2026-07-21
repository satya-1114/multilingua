import type { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface QueueCardProps {
  label: string;
  count: number;
  throughput?: number;
  oldestAgeSeconds?: number;
  tone?: "primary" | "accent" | "warning" | "danger" | "muted";
  actions?: ReactNode;
  children?: ReactNode;
}

const TONES = {
  primary: "border-primary/40",
  accent: "border-violet-500/40",
  warning: "border-amber-500/40",
  danger: "border-rose-500/40",
  muted: "border-border",
} as const;

export function QueueCard({ label, count, throughput, oldestAgeSeconds, tone = "muted", actions, children }: QueueCardProps) {
  return (
    <Card className={cn("shadow-card transition-shadow hover:shadow-elevated border-l-4", TONES[tone])}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
          <p className="mt-1 text-2xl font-semibold tracking-tight text-foreground">{count.toLocaleString()}</p>
        </div>
        {actions}
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {throughput != null && <span>{throughput.toLocaleString()}/min</span>}
          {oldestAgeSeconds != null && oldestAgeSeconds > 0 && <span>Oldest {Math.round(oldestAgeSeconds / 60)}m</span>}
        </div>
        {children && <div className="mt-3">{children}</div>}
      </CardContent>
    </Card>
  );
}
