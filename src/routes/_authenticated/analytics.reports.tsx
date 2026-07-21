import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import { Calendar, Copy, Download, MoreHorizontal, Play, Trash2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { reportService } from "@/services/report.service";

export const Route = createFileRoute("/_authenticated/analytics/reports")({
  component: ReportsPage,
});

function download(name: string, data: string, type = "text/csv") {
  const blob = new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function ReportsPage() {
  const qc = useQueryClient();
  const reports = useQuery({ queryKey: ["reports"], queryFn: () => reportService.list() });

  return (
    <div className="space-y-3">
      {(reports.data ?? []).map((r) => (
        <Card key={r.id} className="shadow-card">
          <CardContent className="flex flex-col gap-3 p-5 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold">{r.name}</p>
                <Badge variant="outline" className="capitalize">{r.kind}</Badge>
                {r.scheduled && <Badge variant="outline"><Calendar className="mr-1 h-3 w-3" />Scheduled</Badge>}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{r.description}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                By {r.createdBy} · Created {format(new Date(r.createdAt), "PP")}
                {r.lastRunAt && ` · Last run ${formatDistanceToNow(new Date(r.lastRunAt), { addSuffix: true })}`}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => reportService.run(r.kind)}>
                <Play className="mr-1 h-3.5 w-3.5" /> Run
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={async () => download(`${r.name}.csv`, await reportService.exportCsv(r.kind))}
              >
                <Download className="mr-1 h-3.5 w-3.5" /> CSV
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={async () =>
                  download(`${r.name}.json`, await reportService.exportJson(r.kind), "application/json")
                }
              >
                <Download className="mr-1 h-3.5 w-3.5" /> JSON
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={async () => {
                  await reportService.duplicate(r.id);
                  qc.invalidateQueries({ queryKey: ["reports"] });
                }}
              >
                <Copy className="mr-1 h-3.5 w-3.5" /> Duplicate
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="text-destructive"
                onClick={async () => {
                  await reportService.remove(r.id);
                  qc.invalidateQueries({ queryKey: ["reports"] });
                }}
              >
                <Trash2 className="mr-1 h-3.5 w-3.5" /> Delete
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
