import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { SystemHealthCard } from "@/components/common/system-health-card";
import { monitoringService } from "@/services/monitoring.service";

export const Route = createFileRoute("/_authenticated/monitoring/health")({
  component: MonitoringHealthPage,
});

function MonitoringHealthPage() {
  const health = useQuery({ queryKey: ["mon", "health"], queryFn: () => monitoringService.health() });
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {(health.data ?? []).map((m) => <SystemHealthCard key={m.id} metric={m} />)}
    </div>
  );
}
