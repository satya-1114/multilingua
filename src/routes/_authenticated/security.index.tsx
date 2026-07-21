import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { SecurityCard } from "@/components/common/security-card";
import { securityService } from "@/services/security.service";
import { ShieldAlert, ShieldCheck, KeySquare, UserX } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/security/")({
  component: SecurityOverview,
});

function SecurityOverview() {
  const qc = useQueryClient();
  const alerts = useQuery({ queryKey: ["sec", "alerts"], queryFn: () => securityService.alerts() });
  const logins = useQuery({ queryKey: ["sec", "logins"], queryFn: () => securityService.logins() });
  const sessions = useQuery({ queryKey: ["sec", "sessions"], queryFn: () => securityService.sessions() });

  const acknowledge = useMutation({ mutationFn: (id: string) => securityService.acknowledgeAlert(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["sec", "alerts"] }) });
  const resolve = useMutation({ mutationFn: (id: string) => securityService.resolveAlert(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["sec", "alerts"] }) });

  const failed = (logins.data ?? []).filter((l) => l.status === "failed").length;
  const blocked = (logins.data ?? []).filter((l) => l.status === "blocked").length;
  const activeAlerts = (alerts.data ?? []).filter((a) => a.status !== "resolved").length;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <AnalyticsCard label="Active alerts" value={activeAlerts} icon={ShieldAlert} />
        <AnalyticsCard label="Active sessions" value={sessions.data?.length ?? 0} icon={ShieldCheck} />
        <AnalyticsCard label="Failed logins / 30d" value={failed} icon={KeySquare} />
        <AnalyticsCard label="Blocked users" value={blocked} icon={UserX} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {(alerts.data ?? []).map((a) => (
          <SecurityCard
            key={a.id}
            alert={a}
            onAcknowledge={(x) => acknowledge.mutate(x.id)}
            onResolve={(x) => resolve.mutate(x.id)}
          />
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">Login history</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Time</th>
                  <th className="px-3 py-2 text-left font-medium">User</th>
                  <th className="px-3 py-2 text-left font-medium">Location</th>
                  <th className="px-3 py-2 text-left font-medium">IP</th>
                  <th className="px-3 py-2 text-left font-medium">Method</th>
                  <th className="px-3 py-2 text-left font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(logins.data ?? []).slice(0, 15).map((l) => (
                  <tr key={l.id}>
                    <td className="whitespace-nowrap px-3 py-2 text-xs">{format(new Date(l.at), "MMM d HH:mm")}</td>
                    <td className="px-3 py-2">{l.actor}</td>
                    <td className="px-3 py-2">{l.location}</td>
                    <td className="px-3 py-2 font-mono text-xs">{l.ip}</td>
                    <td className="px-3 py-2 capitalize">{l.method}</td>
                    <td className="px-3 py-2">
                      <Badge
                        variant="outline"
                        className={cn(
                          "capitalize",
                          l.status === "success" ? "text-success" : l.status === "failed" ? "text-warning" : "text-destructive",
                        )}
                      >
                        {l.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
