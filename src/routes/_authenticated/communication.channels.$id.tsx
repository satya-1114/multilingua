import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChannelBadge } from "@/components/common/channel-badge";
import { ChannelStatistics } from "@/components/common/channel-statistics";
import { DeliveryHealthCard } from "@/components/common/delivery-health-card";
import { StatusBadge } from "@/components/common/status-badge";
import { MessagePreview } from "@/components/common/message-preview";
import { channelService } from "@/services/channel.service";
import { toast } from "sonner";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/_authenticated/communication/channels/$id")({
  component: ChannelDetailPage,
});

function ChannelDetailPage() {
  const { id } = Route.useParams();
  const q = useQuery({ queryKey: ["channel", id], queryFn: async () => {
    const c = await channelService.get(id);
    if (!c) throw notFound();
    return c;
  }});
  const [recipient, setRecipient] = useState("+91-9800000000");
  const [message, setMessage] = useState("Hello from Multilingua — this is a test message.");
  const c = q.data;
  if (!c) return null;
  return (
    <div className="space-y-4">
      <Button asChild variant="ghost" size="sm"><Link to="/communication/channels"><ArrowLeft className="mr-2 h-4 w-4" />Back to channels</Link></Button>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{c.name}</h2>
          <p className="text-sm text-muted-foreground">{c.provider}</p>
          <div className="mt-2 flex gap-2"><ChannelBadge channel={c.kind} /><StatusBadge status={c.status} /></div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={async () => { await channelService.setStatus(c.id, c.status === "active" ? "paused" : "active"); q.refetch(); }}>
            {c.status === "active" ? "Pause" : "Activate"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Configuration</CardTitle></CardHeader>
          <CardContent>
            <dl className="grid gap-3 sm:grid-cols-2">
              <Field label="Sender name" value={c.sender.displayName} />
              <Field label="Sender address" value={c.sender.address} />
              <Field label="Verified" value={c.sender.verified ? "Yes" : "No"} />
              <Field label="Retry policy" value={`${c.retry.policyId} · ${c.retry.maxAttempts}×`} />
              <Field label="Per minute" value={c.limits.perMinute.toLocaleString()} />
              <Field label="Per hour" value={c.limits.perHour.toLocaleString()} />
              <Field label="Per day" value={c.limits.perDay.toLocaleString()} />
              <Field label="Per month" value={c.limits.perMonth.toLocaleString()} />
              {Object.entries(c.configuration).map(([k, v]) => <Field key={k} label={k} value={v} />)}
            </dl>
          </CardContent>
        </Card>
        <div className="space-y-3">
          <ChannelStatistics channel={c} />
          <DeliveryHealthCard channel={c} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Send test message</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2"><Label>Recipient</Label><Input value={recipient} onChange={(e) => setRecipient(e.target.value)} /></div>
            <div className="grid gap-2"><Label>Message</Label><Textarea rows={4} value={message} onChange={(e) => setMessage(e.target.value)} /></div>
            <Button onClick={async () => {
              const r = await channelService.test({ channelId: c.id, recipient, message });
              toast[r.ok ? "success" : "error"](r.ok ? `Delivered in ${r.latencyMs}ms · ${r.providerMessageId}` : r.error ?? "Failed");
            }}>Send test</Button>
          </CardContent>
        </Card>
        <MessagePreview channel={c.kind} sender={c.sender.displayName} body={message} />
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div><dt className="text-xs text-muted-foreground">{label}</dt><dd className="text-sm font-medium">{value}</dd></div>
  );
}
