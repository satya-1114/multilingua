import { formatDistanceToNow } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Webhook } from "@/types/integration";

interface WebhookCardProps {
  webhook: Webhook;
  onTest?: (w: Webhook) => void;
  onToggle?: (w: Webhook) => void;
  onDelete?: (w: Webhook) => void;
}

export function WebhookCard({ webhook, onTest, onToggle, onDelete }: WebhookCardProps) {
  return (
    <Card className="shadow-card">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-sm font-semibold">{webhook.name}</p>
              <Badge variant="outline" className="capitalize">{webhook.direction}</Badge>
              <Badge
                variant="outline"
                className={cn(webhook.active ? "border-success/30 text-success" : "border-border text-muted-foreground")}
              >
                {webhook.active ? "Active" : "Paused"}
              </Badge>
            </div>
            <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{webhook.url}</p>
            <p className="mt-2 text-xs text-muted-foreground">Event: <span className="font-mono">{webhook.event}</span></p>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
          <div>
            <p className="text-muted-foreground">Success</p>
            <p className="font-semibold text-success">{webhook.successCount.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Failed</p>
            <p className="font-semibold text-destructive">{webhook.failureCount.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Last</p>
            <p className="font-semibold">
              {webhook.lastDeliveryAt ? formatDistanceToNow(new Date(webhook.lastDeliveryAt), { addSuffix: true }) : "—"}
            </p>
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <Button size="sm" variant="outline" className="h-8" onClick={() => onTest?.(webhook)}>Test</Button>
          <Button size="sm" variant="outline" className="h-8" onClick={() => onToggle?.(webhook)}>
            {webhook.active ? "Pause" : "Resume"}
          </Button>
          <Button size="sm" variant="ghost" className="h-8 text-destructive" onClick={() => onDelete?.(webhook)}>Delete</Button>
        </div>
      </CardContent>
    </Card>
  );
}
