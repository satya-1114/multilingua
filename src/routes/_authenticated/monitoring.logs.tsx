import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MonitoringTable } from "@/components/common/monitoring-table";
import { monitoringService } from "@/services/monitoring.service";
import type { LogEntry } from "@/types/monitoring";

export const Route = createFileRoute("/_authenticated/monitoring/logs")({
  component: MonitoringLogsPage,
});

function MonitoringLogsPage() {
  const [level, setLevel] = useState<LogEntry["level"] | "all">("all");
  const [search, setSearch] = useState("");
  const logs = useQuery({ queryKey: ["mon", "logs", level, search], queryFn: () => monitoringService.logs({ level, search }) });

  function exportCsv() {
    const rows = logs.data ?? [];
    const header = "time,level,service,message,actor,request";
    const body = rows.map((r) => [r.at, r.level, r.service, JSON.stringify(r.message), r.actor ?? "", r.requestId ?? ""].join(","));
    const blob = new Blob([header + "\n" + body.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "logs.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap items-center gap-2 p-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search logs…" className="pl-8" />
          </div>
          <Select value={level} onValueChange={(v) => setLevel(v as typeof level)}>
            <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All levels</SelectItem>
              <SelectItem value="info">Info</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
              <SelectItem value="error">Error</SelectItem>
              <SelectItem value="debug">Debug</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={exportCsv}><Download className="mr-1 h-4 w-4" /> Export</Button>
        </CardContent>
      </Card>
      <MonitoringTable rows={logs.data ?? []} />
    </div>
  );
}
