import type { LucideIcon } from "lucide-react";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  delta?: string;
  trend?: "up" | "down" | "flat";
  helper?: string;
  icon?: LucideIcon;
  index?: number;
}

const trendClasses: Record<NonNullable<StatCardProps["trend"]>, string> = {
  up: "text-success",
  down: "text-destructive",
  flat: "text-muted-foreground",
};

const trendIcons = { up: ArrowUp, down: ArrowDown, flat: Minus } as const;

export function StatCard({
  label,
  value,
  delta,
  trend = "flat",
  helper,
  icon: Icon,
  index = 0,
}: StatCardProps) {
  const TrendIcon = trendIcons[trend];
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, delay: Math.min(index * 0.04, 0.2) }}
    >
      <Card className="shadow-card transition-shadow hover:shadow-elevated">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {label}
              </p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
                {value}
              </p>
            </div>
            {Icon && (
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Icon className="h-4 w-4" />
              </div>
            )}
          </div>
          {(delta || helper) && (
            <div className="mt-3 flex items-center gap-1 text-xs font-medium">
              {delta && (
                <span className={cn("flex items-center gap-1", trendClasses[trend])}>
                  <TrendIcon className="h-3.5 w-3.5" /> {delta}
                </span>
              )}
              {helper && <span className="text-muted-foreground">{helper}</span>}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
