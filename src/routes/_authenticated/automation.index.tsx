import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Archive, Copy, PlusCircle } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { automationService } from "@/services/automation.service";

export const Route = createFileRoute("/_authenticated/automation/")({
  head: () => ({ meta: [{ title: "Workflow automation" }, { name: "robots", content: "noindex" }] }),
  component: AutomationIndex,
});

const statusStyles = {
  draft: "border-warning/30 text-warning",
  published: "border-success/30 text-success",
  archived: "border-border text-muted-foreground",
} as const;

function AutomationIndex() {
  const qc = useQueryClient();
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: () => automationService.list() });
  const templates = useQuery({ queryKey: ["workflow-templates"], queryFn: () => automationService.templates() });

  const clone = useMutation({
    mutationFn: (id: string) => automationService.clone(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });
  const archive = useMutation({
    mutationFn: (id: string) => automationService.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });

  return (
    <div className="space-y-5">
        <SectionHeader
          title="Workflow automation"
          description="Design and manage approval, delivery, and orchestration flows."
          actions={<Button><PlusCircle className="mr-1 h-4 w-4" /> New workflow</Button>}
        />

        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Templates</h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(templates.data ?? []).map((t) => (
              <Card key={t.id} className="shadow-card">
                <CardContent className="p-5">
                  <Badge variant="outline">{t.category}</Badge>
                  <p className="mt-2 text-sm font-semibold">{t.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{t.description}</p>
                  <Button variant="outline" size="sm" className="mt-3">Use template</Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Your workflows</h2>
          <div className="space-y-3">
            {(workflows.data ?? []).map((wf) => (
              <Card key={wf.id} className="shadow-card">
                <CardContent className="flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to="/automation/$id"
                        params={{ id: wf.id }}
                        className="text-sm font-semibold hover:underline"
                      >
                        {wf.name}
                      </Link>
                      <Badge variant="outline" className={`capitalize ${statusStyles[wf.status]}`}>{wf.status}</Badge>
                      <Badge variant="outline">v{wf.version}</Badge>
                      <Badge variant="outline">{wf.category}</Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{wf.description}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Updated {formatDistanceToNow(new Date(wf.updatedAt), { addSuffix: true })} by {wf.updatedBy} · {wf.runsThisMonth} runs / mo
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button asChild size="sm" variant="outline">
                      <Link to="/automation/$id" params={{ id: wf.id }}>Open</Link>
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => clone.mutate(wf.id)}>
                      <Copy className="mr-1 h-3.5 w-3.5" /> Clone
                    </Button>
                    <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={() => archive.mutate(wf.id)}>
                      <Archive className="mr-1 h-3.5 w-3.5" /> Archive
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
  );
}
