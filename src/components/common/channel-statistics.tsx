import { Card, CardContent } from "@/components/ui/card";
import { ChannelBadge } from "./channel-badge";
import type { Channel } from "@/types/channel";

export function ChannelStatistics({ channel }: { channel: Channel }) {
  const dailyPct = Math.min(100, Math.round((channel.usage.dailySent / channel.usage.dailyCap) * 100));
  const monthlyPct = Math.min(100, Math.round((channel.usage.monthlySent / channel.usage.monthlyCap) * 100));
  return (
    <Card className="shadow-card">
      <CardContent className="space-y-3 p-4">
        <div className="flex items-center justify-between">
          <ChannelBadge channel={channel.kind} />
          <span className="text-xs text-muted-foreground">Queue · {channel.queueDepth.toLocaleString()}</span>
        </div>
        <Meter label="Daily usage" pct={dailyPct} caption={`${channel.usage.dailySent.toLocaleString()} / ${channel.usage.dailyCap.toLocaleString()}`} />
        <Meter label="Monthly usage" pct={monthlyPct} caption={`${channel.usage.monthlySent.toLocaleString()} / ${channel.usage.monthlyCap.toLocaleString()}`} />
      </CardContent>
    </Card>
  );
}

function Meter({ label, pct, caption }: { label: string; pct: number; caption: string }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground">{pct}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-1 text-[11px] text-muted-foreground">{caption}</p>
    </div>
  );
}
