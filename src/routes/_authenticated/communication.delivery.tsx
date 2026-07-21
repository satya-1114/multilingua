import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Download, Pause, Play, RefreshCw, XCircle, Zap, Copy } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { QueueCard } from "@/components/common/queue-card";
import { DeliveryStatusBadge } from "@/components/common/delivery-status-badge";
import { ChannelBadge } from "@/components/common/channel-badge";
import { DeliveryProgressIndicator } from "@/components/common/delivery-progress-indicator";
import { deliveryService } from "@/services/delivery.service";
import { toast } from "sonner";
import type { DeliveryQueueKind } from "@/types/delivery";
import { useState } from "react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/communication/delivery")({
  component: DeliveryPage,
});

const QUEUE_TONES: Record<DeliveryQueueKind, "primary" | "accent" | "warning" | "danger" | "muted"> = {
  delivery: "primary", processing: "accent", scheduled: "muted", retry: "warning",
  failed: "danger", cancelled: "muted", completed: "muted",
};

function DeliveryPage() {
  const q = useQuery({ queryKey: ["delivery", "queues"], queryFn: () => deliveryService.queues(), refetchInterval: 8000 });
  const [selected, setSelected] = useState<DeliveryQueueKind>("delivery");
  const queues = q.data ?? [];
  const current = queues.find((x) => x.kind === selected);

  async function act(fn: () => Promise<{ ok: boolean; message: string }>) {
    const r = await fn();
    toast[r.ok ? "success" : "error"](r.message);
    q.refetch();
  }

  async function exportCsv() {
    const csv = await deliveryService.exportCsv();
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `delivery-${Date.now()}.csv`; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-7">
        {queues.map((s) => (
          <button key={s.kind} onClick={() => setSelected(s.kind)} className={cn("text-left", selected === s.kind && "ring-2 ring-primary ring-offset-2 ring-offset-background rounded-xl")}>
            <QueueCard label={s.label} count={s.count} throughput={s.throughputPerMinute} oldestAgeSeconds={s.oldestAgeSeconds} tone={QUEUE_TONES[s.kind]} />
          </button>
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm">{current?.label ?? "Queue"}</CardTitle>
          <Button size="sm" variant="outline" onClick={exportCsv}><Download className="mr-2 h-4 w-4" />Export CSV</Button>
        </CardHeader>
        <CardContent>
          {(current?.jobs.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">This queue is empty.</p>
          ) : (
            <div className="divide-y divide-border">
              {current!.jobs.map((j) => (
                <div key={j.id} className="grid gap-3 py-4 lg:grid-cols-[1fr_180px_auto]">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Link to="/campaigns/$id/delivery" params={{ id: j.campaignId }} className="truncate text-sm font-medium hover:underline">
                        {j.campaignName}
                      </Link>
                      <ChannelBadge channel={j.channel} />
                      <DeliveryStatusBadge status={j.status} />
                      <span className="text-xs text-muted-foreground">Priority · {j.priority}</span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">{j.language} · {j.totalRecipients.toLocaleString()} recipients · Attempts {j.attempts}/{j.maxAttempts}</p>
                    <div className="mt-2 max-w-md"><DeliveryProgressIndicator job={j} /></div>
                  </div>
                  <div className="text-xs text-muted-foreground lg:text-right">
                    {j.scheduledAt && <p>Scheduled · {new Date(j.scheduledAt).toLocaleString()}</p>}
                    {j.startedAt && <p>Started · {new Date(j.startedAt).toLocaleString()}</p>}
                    {j.completedAt && <p>Completed · {new Date(j.completedAt).toLocaleString()}</p>}
                  </div>
                  <div className="flex flex-wrap justify-end gap-1">
                    <Button size="sm" variant="ghost" onClick={() => act(() => deliveryService.retry(j.id))}><RefreshCw className="h-3.5 w-3.5" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => act(() => deliveryService.pause(j.id))}><Pause className="h-3.5 w-3.5" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => act(() => deliveryService.resume(j.id))}><Play className="h-3.5 w-3.5" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => act(() => deliveryService.prioritize(j.id))}><Zap className="h-3.5 w-3.5" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => act(() => deliveryService.duplicate(j.id))}><Copy className="h-3.5 w-3.5" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => act(() => deliveryService.cancel(j.id))}><XCircle className="h-3.5 w-3.5" /></Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
