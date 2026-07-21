import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { monitoringService } from "@/services/monitoring.service";
import { Activity, CheckCircle2, ListChecks, RefreshCw } from "lucide-react";

export const Route = createFileRoute("/_authenticated/monitoring/")({
  component: MonitoringOverview,
});

function MonitoringOverview() {
  const services = useQuery({ queryKey: ["mon", "services"], queryFn: () => monitoringService.services() });
  const queues = useQuery({ queryKey: ["mon", "queues"], queryFn: () => monitoringService.queues() });

  const totals = (queues.data ?? []).reduce(
    (a, q) => ({ pending: a.pending + q.pending, running: a.running + q.running, done: a.done + q.completed24h, failed: a.failed + q.failed24h }),
    { pending: 0, running: 0, done: 0, failed: 0 },
  );

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <AnalyticsCard label="Pending" value={totals.pending} icon={ListChecks} />
        <AnalyticsCard label="Running" value={totals.running} icon={RefreshCw} />
        <AnalyticsCard label="Completed / 24h" value={totals.done.toLocaleString()} icon={CheckCircle2} />
        <AnalyticsCard label="Failed / 24h" value={totals.failed} icon={Activity} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Queue snapshot</CardTitle></CardHeader>
          <CardContent>
            <div className="divide-y divide-border">
              {(queues.data ?? []).map((q) => (
                <div key={q.name} className="grid grid-cols-5 items-center gap-2 py-2 text-sm">
                  <span className="col-span-2 font-medium">{q.name}</span>
                  <span><Badge variant="outline">{q.pending} pending</Badge></span>
                  <span><Badge variant="outline">{q.running} running</Badge></span>
                  <span className="text-right text-xs text-muted-foreground">
                    {q.completed24h.toLocaleString()} · <span className="text-destructive">{q.failed24h}</span>
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Service status</CardTitle></CardHeader>
          <CardContent>
            <div className="divide-y divide-border">
              {(services.data ?? []).map((s) => (
                <div key={s.id} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <p className="font-medium">{s.name}</p>
                    <p className="text-xs text-muted-foreground">{s.region} · {s.latencyMs}ms · {s.uptimePercent.toFixed(2)}% uptime</p>
                  </div>
                  <Badge variant="outline" className="capitalize">{s.status}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
