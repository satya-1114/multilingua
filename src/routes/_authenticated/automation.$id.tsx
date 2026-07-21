import { createFileRoute, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { SectionHeader } from "@/components/common/section-header";
import { WorkflowCanvas } from "@/components/common/workflow-canvas";
import { workflowNodeMeta } from "@/components/common/workflow-node";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { automationService } from "@/services/automation.service";
import type { WorkflowNodeKind } from "@/types/automation";

export const Route = createFileRoute("/_authenticated/automation/$id")({
  head: () => ({ meta: [{ title: "Workflow builder" }, { name: "robots", content: "noindex" }] }),
  component: WorkflowDetailPage,
});

const paletteOrder: WorkflowNodeKind[] = [
  "trigger", "approval", "delay", "condition", "audience", "template", "communication", "notification", "ai", "end",
];

function WorkflowDetailPage() {
  const { id } = useParams({ from: "/_authenticated/automation/$id" });
  const qc = useQueryClient();
  const [selected, setSelected] = useState<string | undefined>();

  const workflow = useQuery({ queryKey: ["workflow", id], queryFn: () => automationService.get(id) });
  const publish = useMutation({
    mutationFn: () => automationService.publish(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflow", id] }),
  });

  const wf = workflow.data;
  const selNode = wf?.nodes.find((n) => n.id === selected);

  return (
    <div className="space-y-4">
        <SectionHeader
          title={wf?.name ?? "Workflow"}
          description={wf?.description}
          actions={
            <div className="flex gap-2">
              <Button variant="outline">Save draft</Button>
              <Button onClick={() => publish.mutate()} disabled={publish.isPending}>Publish</Button>
            </div>
          }
        />
        {wf && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge variant="outline" className="capitalize">{wf.status}</Badge>
            <Badge variant="outline">v{wf.version}</Badge>
            <span className="text-muted-foreground">
              Updated {formatDistanceToNow(new Date(wf.updatedAt), { addSuffix: true })} by {wf.updatedBy}
            </span>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-[220px,1fr,280px]">
          <Card>
            <CardHeader><CardTitle className="text-sm">Palette</CardTitle></CardHeader>
            <CardContent className="space-y-1.5">
              {paletteOrder.map((k) => {
                const meta = workflowNodeMeta[k];
                const Icon = meta.icon;
                return (
                  <div key={k} className="flex items-center gap-2 rounded-lg border p-2 text-xs">
                    <div className="flex h-6 w-6 items-center justify-center rounded" style={{ background: meta.color }}>
                      <Icon className="h-3.5 w-3.5 text-white" />
                    </div>
                    <span>{meta.label}</span>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <div>
            {wf ? (
              <WorkflowCanvas workflow={wf} selectedId={selected} onSelect={setSelected} />
            ) : (
              <Card><CardContent className="p-8 text-sm text-muted-foreground">Loading workflow…</CardContent></Card>
            )}
          </div>

          <Card>
            <CardHeader><CardTitle className="text-sm">Node inspector</CardTitle></CardHeader>
            <CardContent>
              {selNode ? (
                <div className="space-y-2 text-sm">
                  <p className="font-semibold">{selNode.title}</p>
                  <p className="text-xs text-muted-foreground capitalize">{selNode.kind}</p>
                  {selNode.description && <p className="text-xs">{selNode.description}</p>}
                  <p className="text-[11px] text-muted-foreground">Position: {selNode.x}, {selNode.y}</p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Select a node to configure it.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
  );
}
