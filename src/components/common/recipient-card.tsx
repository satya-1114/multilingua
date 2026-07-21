import { format } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { DeliveryStatusBadge } from "./delivery-status-badge";
import { ChannelBadge } from "./channel-badge";
import { LanguageBadge } from "./language-badge";
import type { DeliveryRecipient } from "@/types/delivery";

export function RecipientCard({ recipient }: { recipient: DeliveryRecipient }) {
  return (
    <Card className="shadow-card">
      <CardContent className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{recipient.name}</p>
          <p className="truncate text-xs text-muted-foreground">{recipient.address}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <ChannelBadge channel={recipient.channel} />
            <LanguageBadge code={recipient.language} />
            {recipient.device && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{recipient.device}</span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <DeliveryStatusBadge status={recipient.status} />
          <span className="text-[11px] text-muted-foreground">Attempts · {recipient.attempts}</span>
          {recipient.deliveredAt && (
            <span className="text-[11px] text-muted-foreground">{format(new Date(recipient.deliveredAt), "MMM d, HH:mm")}</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
