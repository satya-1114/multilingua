import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { Activity, GitCommit, Server, Users2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { systemService } from "@/services/system.service";
import { workspaceService } from "@/services/workspace.service";

export const Route = createFileRoute("/_authenticated/admin/")({
  component: AdminIndexPage,
});

function AdminIndexPage() {
  const version = useQuery({ queryKey: ["admin", "version"], queryFn: () => systemService.version() });
  const license = useQuery({ queryKey: ["admin", "license"], queryFn: () => systemService.license() });
  const notes = useQuery({ queryKey: ["admin", "release"], queryFn: () => systemService.releaseNotes() });
  const workspaces = useQuery({ queryKey: ["workspace", "all"], queryFn: () => workspaceService.list() });

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        <AnalyticsCard label="Workspaces" value={workspaces.data?.length ?? 0} icon={Users2} />
        <AnalyticsCard label="Seats used" value={`${license.data?.seatsUsed ?? 0}/${license.data?.seats ?? 0}`} icon={Users2} />
        <AnalyticsCard label="Environment" value={version.data?.environment ?? "—"} icon={Server} />
        <AnalyticsCard label="Version" value={version.data?.version ?? "—"} icon={GitCommit} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Release notes</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {(notes.data ?? []).map((n) => (
              <div key={n.version} className="border-l-2 border-primary pl-3">
                <div className="flex items-baseline justify-between">
                  <p className="text-sm font-semibold">{n.title}</p>
                  <span className="font-mono text-xs text-muted-foreground">v{n.version}</span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">{format(new Date(n.date), "PP")}</p>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                  {n.highlights.map((h) => <li key={h}>{h}</li>)}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Environment overview</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Row label="Version" value={version.data?.version ?? "—"} />
            <Row label="Environment" value={version.data?.environment ?? "—"} />
            <Row label="Commit" value={version.data?.commit ?? "—"} />
            <Row label="Built at" value={version.data ? format(new Date(version.data.builtAt), "PPpp") : "—"} />
            <Row label="Plan" value={license.data?.plan ?? "—"} />
            <Row label="Contract" value={license.data?.contractId ?? "—"} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border px-3 py-2">
      <span className="text-xs uppercase text-muted-foreground">{label}</span>
      <span className="font-mono text-xs">{value}</span>
    </div>
  );
}
