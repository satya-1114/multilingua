import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { SectionHeader } from "@/components/common/section-header";
import { WebhookCard } from "@/components/common/webhook-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { integrationService } from "@/services/integration.service";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/integrations/webhooks")({
  head: () => ({ meta: [{ title: "Webhooks" }, { name: "robots", content: "noindex" }] }),
  component: WebhooksPage,
});

const statusStyles = {
  success: "text-success",
  failed: "text-destructive",
  retrying: "text-warning",
} as const;

function WebhooksPage() {
  const qc = useQueryClient();
  const webhooks = useQuery({ queryKey: ["webhooks"], queryFn: () => integrationService.webhooks() });
  const deliveries = useQuery({ queryKey: ["webhook-deliveries"], queryFn: () => integrationService.deliveries() });

  const test = useMutation({
    mutationFn: (id: string) => integrationService.testWebhook(id),
    onSuccess: (r) => toast.success(`Test delivered · ${r.status} · ${r.latencyMs}ms`),
  });
  const toggle = useMutation({
    mutationFn: (id: string) => integrationService.toggleWebhook(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => integrationService.deleteWebhook(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["webhooks"] }),
  });

  return (
    <div className="space-y-5">
        <SectionHeader title="Webhook manager" description="Manage incoming and outgoing webhooks with retries and validation." />

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(webhooks.data ?? []).map((w) => (
            <WebhookCard
              key={w.id}
              webhook={w}
              onTest={(x) => test.mutate(x.id)}
              onToggle={(x) => toggle.mutate(x.id)}
              onDelete={(x) => remove.mutate(x.id)}
            />
          ))}
        </div>

        <Card>
          <CardHeader><CardTitle className="text-base">Recent deliveries</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Time</th>
                    <th className="px-3 py-2 text-left font-medium">Webhook</th>
                    <th className="px-3 py-2 text-left font-medium">Status</th>
                    <th className="px-3 py-2 text-left font-medium">Code</th>
                    <th className="px-3 py-2 text-left font-medium">Attempt</th>
                    <th className="px-3 py-2 text-left font-medium">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(deliveries.data ?? []).map((d) => (
                    <tr key={d.id}>
                      <td className="whitespace-nowrap px-3 py-2 text-xs">{format(new Date(d.at), "MMM d HH:mm:ss")}</td>
                      <td className="px-3 py-2 font-mono text-xs">{d.webhookId}</td>
                      <td className="px-3 py-2">
                        <Badge variant="outline" className={`capitalize ${statusStyles[d.status]}`}>{d.status}</Badge>
                      </td>
                      <td className="px-3 py-2 font-mono">{d.responseCode}</td>
                      <td className="px-3 py-2">{d.attempt}</td>
                      <td className="px-3 py-2 font-mono">{d.latencyMs}ms</td>
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
