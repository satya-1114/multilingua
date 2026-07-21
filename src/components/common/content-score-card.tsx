import { motion } from "framer-motion";
import type { AiContentScores } from "@/types/ai";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const LABELS: Record<keyof AiContentScores, string> = {
  readability: "Readability",
  engagement: "Engagement",
  sentiment: "Sentiment",
  contentScore: "Content score",
  seoScore: "SEO",
  accessibility: "Accessibility",
};

function toneFor(value: number) {
  if (value >= 85) return "text-success";
  if (value >= 70) return "text-primary";
  return "text-warning";
}

interface ContentScoreCardProps {
  scores: AiContentScores;
  compact?: boolean;
}

export function ContentScoreCard({ scores, compact }: ContentScoreCardProps) {
  const entries = Object.entries(scores) as [keyof AiContentScores, number][];
  return (
    <Card>
      <CardContent className={cn("p-4", compact && "p-3")}>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Content scores
        </p>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {entries.map(([key, value], i) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="rounded-lg border border-border/70 bg-card px-3 py-2"
            >
              <p className="text-[11px] font-medium text-muted-foreground">{LABELS[key]}</p>
              <p className={cn("mt-1 text-lg font-semibold tabular-nums", toneFor(value))}>
                {value}
                <span className="ml-0.5 text-xs text-muted-foreground">/100</span>
              </p>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                <motion.div
                  className={cn(
                    "h-full rounded-full",
                    value >= 85
                      ? "bg-success"
                      : value >= 70
                        ? "bg-primary"
                        : "bg-warning",
                  )}
                  initial={{ width: 0 }}
                  animate={{ width: `${value}%` }}
                  transition={{ duration: 0.6, delay: i * 0.03 }}
                />
              </div>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
