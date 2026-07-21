import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Gauge, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { productionService } from "@/services/production.service";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/admin/readiness")({
  head: () => ({ meta: [{ title: "Production readiness" }, { name: "robots", content: "noindex" }] }),
  component: ReadinessPage,
});

function ReadinessPage() {
  const q = useQuery({ queryKey: ["admin", "readiness"], queryFn: () => productionService.report() });
  const report = q.data;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <AnalyticsCard label="Readiness score" value={report ? `${report.overallScore}%` : "—"} icon={Gauge} />
        <AnalyticsCard label="Environment" value={report?.environment ?? "—"} icon={ShieldCheck} />
        <AnalyticsCard label="Mock API" value={report ? (report.mock ? "Enabled" : "Disabled") : "—"} icon={AlertTriangle} />
        <AnalyticsCard label="API version" value={report?.version ?? "—"} icon={CheckCircle2} />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="text-base">Readiness signals</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {(report?.signals ?? []).map((s) => (
              <div key={s.key} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{s.label}</span>
                    <Badge variant="secondary" className={cn(
                      s.status === "ready" && "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
                      s.status === "warning" && "bg-amber-500/10 text-amber-700 dark:text-amber-400",
                      s.status === "blocked" && "bg-destructive/10 text-destructive",
                    )}>{s.status}</Badge>
                  </div>
                  <span className="tabular-nums text-muted-foreground">{s.score}%</span>
                </div>
                <Progress value={s.score} className="h-1.5" />
                <p className="text-xs text-muted-foreground">{s.detail}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader><CardTitle className="text-base">Warnings</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm">
              {report?.warnings.length ? report.warnings.map((w) => (
                <div key={w} className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 p-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-600" />
                  <span>{w}</span>
                </div>
              )) : <p className="text-muted-foreground">No warnings.</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Pending tasks</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {(report?.pendingTasks ?? []).map((t) => (
                  <li key={t} className="flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary" />
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Feature flags</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {(report?.featureFlags ?? []).map((f) => (
              <div key={f.key} className="flex items-center justify-between rounded-md border p-2">
                <span className="font-mono text-xs">{f.key}</span>
                <Badge variant={f.enabled ? "default" : "secondary"}>{f.enabled ? "Enabled" : "Disabled"}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Bundle</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-baseline justify-between">
              <span className="text-muted-foreground">Estimated first-load JS</span>
              <span className="text-2xl font-semibold tabular-nums">{report?.bundle.estimatedKb ?? "—"} KB</span>
            </div>
            <p className="text-xs text-muted-foreground">{report?.bundle.note}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
