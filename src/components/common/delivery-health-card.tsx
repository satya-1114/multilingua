import { Activity, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Channel } from "@/types/channel";

export function DeliveryHealthCard({ channel }: { channel: Channel }) {
  const { score, latencyMs, successRate, incidents24h } = channel.health;
  const tone = score >= 95 ? "success" : score >= 80 ? "warning" : "danger";
  const toneClasses = {
    success: "text-emerald-600 bg-emerald-500/10",
    warning: "text-amber-600 bg-amber-500/10",
    danger: "text-rose-600 bg-rose-500/10",
  } as const;
  const Icon = tone === "success" ? CheckCircle2 : tone === "warning" ? Activity : AlertTriangle;

  return (
    <Card className="shadow-card">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-sm font-medium text-muted-foreground">{channel.name}</CardTitle>
          <p className="text-xs text-muted-foreground">{channel.provider}</p>
        </div>
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg", toneClasses[tone])}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold">{score}</span>
          <span className="text-xs text-muted-foreground">health score</span>
        </div>
        <dl className="grid grid-cols-3 gap-2 text-xs">
          <div><dt className="text-muted-foreground">Latency</dt><dd className="font-medium">{latencyMs}ms</dd></div>
          <div><dt className="text-muted-foreground">Success</dt><dd className="font-medium">{successRate}%</dd></div>
          <div><dt className="text-muted-foreground">Incidents</dt><dd className="font-medium">{incidents24h}</dd></div>
        </dl>
      </CardContent>
    </Card>
  );
}
