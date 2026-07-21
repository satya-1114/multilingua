import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { systemService } from "@/services/system.service";

export const Route = createFileRoute("/_authenticated/admin/feature-flags")({
  component: FeatureFlagsPage,
});

function FeatureFlagsPage() {
  const qc = useQueryClient();
  const flags = useQuery({ queryKey: ["admin", "flags"], queryFn: () => systemService.flags() });
  const refresh = () => qc.invalidateQueries({ queryKey: ["admin", "flags"] });

  async function toggle(key: string) {
    await systemService.toggleFlag(key);
    refresh();
  }
  async function setRollout(key: string, pct: number) {
    await systemService.setRollout(key, pct);
    refresh();
  }

  return (
    <div className="space-y-3">
      {(flags.data ?? []).map((f) => (
        <Card key={f.key} className="shadow-card">
          <CardContent className="p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold">{f.name}</p>
                  <Badge variant="outline" className="font-mono text-[10px]">{f.key}</Badge>
                  <Badge variant="outline" className="capitalize">{f.scope}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{f.description}</p>
                <p className="mt-2 text-[11px] text-muted-foreground">
                  Updated {formatDistanceToNow(new Date(f.updatedAt), { addSuffix: true })} by {f.updatedBy}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">{f.enabled ? "Enabled" : "Disabled"}</span>
                <Switch checked={f.enabled} onCheckedChange={() => toggle(f.key)} />
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Rollout</span>
                <span className="font-mono">{f.rolloutPercent}%</span>
              </div>
              <Slider
                value={[f.rolloutPercent]}
                max={100}
                step={10}
                onValueCommit={(v) => setRollout(f.key, v[0])}
                className="mt-2"
              />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
