import { formatDistanceToNow } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChannelBadge } from "./channel-badge";
import { DeliveryStatusBadge } from "./delivery-status-badge";
import type { DeliveryJob } from "@/types/delivery";

export function CommunicationActivityFeed({ jobs, title = "Recent activity" }: { jobs: DeliveryJob[]; title?: string }) {
  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2"><CardTitle className="text-sm">{title}</CardTitle></CardHeader>
      <CardContent>
        {jobs.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing to show yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {jobs.map((j) => (
              <li key={j.id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{j.campaignName}</p>
                  <div className="mt-1 flex items-center gap-2">
                    <ChannelBadge channel={j.channel} />
                    <span className="text-xs text-muted-foreground">{j.language} · {j.totalRecipients.toLocaleString()} recipients</span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <DeliveryStatusBadge status={j.status} />
                  <span className="text-[11px] text-muted-foreground">{formatDistanceToNow(new Date(j.updatedAt), { addSuffix: true })}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
