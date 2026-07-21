import type { LucideIcon } from "lucide-react";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface AnalyticsCardProps {
  label: string;
  value: string | number;
  delta?: number;
  helper?: string;
  icon?: LucideIcon;
}

export function AnalyticsCard({ label, value, delta, helper, icon: Icon }: AnalyticsCardProps) {
  const trend = delta == null ? "flat" : delta > 0 ? "up" : delta < 0 ? "down" : "flat";
  const TrendIcon = trend === "up" ? ArrowUp : trend === "down" ? ArrowDown : Minus;
  const tone = trend === "up" ? "text-success" : trend === "down" ? "text-destructive" : "text-muted-foreground";
  const display = typeof value === "number" ? value.toLocaleString() : value;
  return (
    <Card className="shadow-card">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-tight">{display}</p>
          </div>
          {Icon && (
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="h-4 w-4" />
            </div>
          )}
        </div>
        {(delta != null || helper) && (
          <div className="mt-3 flex items-center gap-2 text-xs font-medium">
            {delta != null && (
              <span className={cn("inline-flex items-center gap-1", tone)}>
                <TrendIcon className="h-3.5 w-3.5" />
                {Math.abs(delta).toFixed(1)}%
              </span>
            )}
            {helper && <span className="text-muted-foreground">{helper}</span>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
