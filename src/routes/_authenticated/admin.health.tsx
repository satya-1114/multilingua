import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, CircleAlert, Wrench } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { SystemHealthCard } from "@/components/common/system-health-card";
import { monitoringService } from "@/services/monitoring.service";
import { systemService } from "@/services/system.service";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/admin/health")({
  component: AdminHealthPage,
});

const statusStyles = {
  operational: "text-success",
  degraded: "text-warning",
  outage: "text-destructive",
  maintenance: "text-primary",
} as const;

function AdminHealthPage() {
  const qc = useQueryClient();
  const services = useQuery({ queryKey: ["mon", "services"], queryFn: () => monitoringService.services() });
  const health = useQuery({ queryKey: ["mon", "health"], queryFn: () => monitoringService.health() });
  const maintenance = useQuery({ queryKey: ["admin", "maintenance"], queryFn: () => systemService.maintenance() });

  return (
    <div className="space-y-5">
      <Card className="shadow-card">
        <CardContent className="flex items-center justify-between p-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10 text-warning">
              <Wrench className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold">Maintenance mode</p>
              <p className="text-xs text-muted-foreground">Temporarily suspend outgoing campaigns and disable non-admin access.</p>
            </div>
          </div>
          <Switch
            checked={Boolean(maintenance.data)}
            onCheckedChange={async (v) => {
              await systemService.setMaintenance(v);
              qc.invalidateQueries({ queryKey: ["admin", "maintenance"] });
            }}
          />
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-3">
        {(health.data ?? []).map((m) => <SystemHealthCard key={m.id} metric={m} />)}
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Service status</CardTitle></CardHeader>
        <CardContent>
          <div className="divide-y divide-border">
            {(services.data ?? []).map((s) => {
              const Icon = s.status === "operational" ? CheckCircle2 : s.status === "degraded" ? AlertTriangle : CircleAlert;
              return (
                <div key={s.id} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-3">
                    <Icon className={cn("h-4 w-4", statusStyles[s.status])} />
                    <div>
                      <p className="text-sm font-medium">{s.name}</p>
                      <p className="text-xs text-muted-foreground">{s.region}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <Badge variant="outline" className={cn("capitalize", statusStyles[s.status])}>{s.status}</Badge>
                    <span className="font-mono text-muted-foreground">{s.latencyMs} ms</span>
                    <span className="font-mono text-muted-foreground">{s.uptimePercent.toFixed(2)}%</span>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
