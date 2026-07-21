import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Star, Users, Database, Zap } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { workspaceService } from "@/services/workspace.service";
import { eventBus } from "@/services/event-bus.service";

export const Route = createFileRoute("/_authenticated/workspaces")({
  head: () => ({ meta: [{ title: "Workspaces" }, { name: "robots", content: "noindex" }] }),
  component: WorkspacesPage,
});

function WorkspacesPage() {
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["workspace", "all"], queryFn: () => workspaceService.list() });
  const cur = useQuery({ queryKey: ["workspace", "current"], queryFn: () => workspaceService.current() });

  async function pick(id: string) {
    await workspaceService.switchTo(id);
    eventBus.emit("workspace:switched", { workspaceId: id });
    await qc.invalidateQueries({ queryKey: ["workspace"] });
  }
  async function star(id: string) {
    await workspaceService.toggleFavorite(id);
    await qc.invalidateQueries({ queryKey: ["workspace"] });
  }

  return (
    <div className="space-y-6">
        <SectionHeader
          title="Workspaces"
          description="Switch between tenants, review usage, and manage per-workspace settings."
        />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(list.data ?? []).map((w) => {
            const isCurrent = cur.data?.id === w.id;
            const storagePct = (w.storageUsedGb / w.storageQuotaGb) * 100;
            const apiPct = (w.apiUsedThisMonth / w.apiQuotaMonthly) * 100;
            return (
              <Card key={w.id} className="shadow-card">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold text-white"
                        style={{ background: w.colorAccent }}
                      >
                        {w.name.split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-semibold">{w.name}</p>
                        <p className="text-xs text-muted-foreground">{w.organizationType} · {w.region}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isCurrent && <Badge>Current</Badge>}
                      <Badge variant="outline" className="capitalize">{w.plan}</Badge>
                    </div>
                  </div>

                  <div className="mt-4 space-y-3">
                    <MetricRow icon={Users} label="Members" value={String(w.memberCount)} />
                    <MetricRow icon={Database} label="Storage" value={`${w.storageUsedGb.toFixed(1)} / ${w.storageQuotaGb} GB`}>
                      <Progress value={storagePct} className="h-1.5" />
                    </MetricRow>
                    <MetricRow icon={Zap} label="API calls / mo" value={`${w.apiUsedThisMonth.toLocaleString()} / ${w.apiQuotaMonthly.toLocaleString()}`}>
                      <Progress value={apiPct} className="h-1.5" />
                    </MetricRow>
                  </div>

                  <div className="mt-4 flex items-center justify-between gap-2">
                    <div className="flex flex-wrap gap-1">
                      {w.languages.slice(0, 4).map((l) => (
                        <Badge key={l} variant="outline" className="uppercase">{l}</Badge>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="icon" onClick={() => star(w.id)} aria-label="Favorite">
                        <Star className={w.isFavorite ? "h-4 w-4 fill-current text-warning" : "h-4 w-4"} />
                      </Button>
                      <Button variant={isCurrent ? "outline" : "default"} size="sm" onClick={() => pick(w.id)}>
                        {isCurrent ? "Current" : "Switch"}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
  );
}

function MetricRow({
  icon: Icon,
  label,
  value,
  children,
}: {
  icon: typeof Building2;
  label: string;
  value: string;
  children?: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 text-muted-foreground">
          <Icon className="h-3.5 w-3.5" /> {label}
        </span>
        <span className="font-medium">{value}</span>
      </div>
      {children && <div className="mt-1">{children}</div>}
    </div>
  );
}
