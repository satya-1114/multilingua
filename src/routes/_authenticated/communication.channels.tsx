import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChannelBadge, channelLabel } from "@/components/common/channel-badge";
import { ChannelStatistics } from "@/components/common/channel-statistics";
import { DeliveryHealthCard } from "@/components/common/delivery-health-card";
import { StatusBadge } from "@/components/common/status-badge";
import { channelService } from "@/services/channel.service";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/communication/channels")({
  component: ChannelsPage,
});

function ChannelsPage() {
  const q = useQuery({ queryKey: ["channels"], queryFn: () => channelService.list() });
  const channels = q.data ?? [];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {channels.map((c) => (
          <Card key={c.id} className="shadow-card">
            <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
              <div>
                <CardTitle className="text-base">{c.name}</CardTitle>
                <p className="text-xs text-muted-foreground">{c.provider}</p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <ChannelBadge channel={c.kind} />
                <StatusBadge status={c.status} />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-lg bg-muted/40 p-3 text-sm">
                <p className="text-xs text-muted-foreground">Sender</p>
                <p className="font-medium">{c.sender.displayName}</p>
                <p className="text-xs text-muted-foreground">{c.sender.address}{c.sender.verified ? " · Verified" : ""}</p>
              </div>
              <ChannelStatistics channel={c} />
              <div className="flex flex-wrap gap-2">
                <Button asChild size="sm" variant="outline">
                  <Link to="/communication/channels/$id" params={{ id: c.id }}>Configure</Link>
                </Button>
                <Button size="sm" variant="outline"
                  onClick={async () => {
                    const r = await channelService.test({ channelId: c.id, recipient: "+91-9800000000", message: "Test" });
                    toast[r.ok ? "success" : "error"](r.ok ? `Test sent (${r.latencyMs}ms)` : r.error ?? "Failed");
                  }}
                >Send test</Button>
                <Button size="sm" variant="ghost"
                  onClick={async () => {
                    await channelService.setStatus(c.id, c.status === "active" ? "paused" : "active");
                    q.refetch();
                  }}
                >{c.status === "active" ? "Pause" : "Activate"}</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div>
        <h3 className="mb-3 text-sm font-semibold text-muted-foreground">Delivery health</h3>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {channels.map((c) => <DeliveryHealthCard key={c.id} channel={c} />)}
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Channel roster</CardTitle></CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          Available channels: {channels.map((c) => channelLabel(c.kind)).join(" · ")}.
        </CardContent>
      </Card>
    </div>
  );
}
