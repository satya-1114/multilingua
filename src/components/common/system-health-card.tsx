import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { HealthMetric } from "@/types/monitoring";

const toneMap = {
  healthy: "text-success",
  warning: "text-warning",
  critical: "text-destructive",
} as const;

export function SystemHealthCard({ metric }: { metric: HealthMetric }) {
  const pct = Math.min(100, (metric.value / metric.threshold) * 100);
  return (
    <Card className="shadow-card">
      <CardContent className="p-5">
        <div className="flex items-baseline justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{metric.label}</p>
          <p className={cn("text-xs font-semibold capitalize", toneMap[metric.status])}>{metric.status}</p>
        </div>
        <p className="mt-2 text-2xl font-semibold">
          {metric.value}
          <span className="ml-1 text-sm text-muted-foreground">{metric.unit}</span>
        </p>
        <Progress value={pct} className="mt-3 h-1.5" />
        <p className="mt-2 text-[11px] text-muted-foreground">
          Threshold {metric.threshold}
          {metric.unit}
        </p>
      </CardContent>
    </Card>
  );
}
