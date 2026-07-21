import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDistanceToNow } from "date-fns";
import type { Integration } from "@/types/integration";
import { cn } from "@/lib/utils";

const statusStyles: Record<Integration["status"], string> = {
  connected: "bg-success/10 text-success border-success/20",
  disconnected: "bg-muted text-muted-foreground border-border",
  error: "bg-destructive/10 text-destructive border-destructive/20",
  pending: "bg-warning/10 text-warning border-warning/20",
};

interface IntegrationCardProps {
  integration: Integration;
  onConfigure?: (i: Integration) => void;
  onToggle?: (i: Integration) => void;
}

export function IntegrationCard({ integration, onConfigure, onToggle }: IntegrationCardProps) {
  return (
    <Card className="shadow-card transition-shadow hover:shadow-elevated">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className="flex h-11 w-11 items-center justify-center rounded-lg text-sm font-semibold text-white"
              style={{ background: integration.color }}
            >
              {integration.logoInitials}
            </div>
            <div>
              <p className="text-sm font-semibold">{integration.provider}</p>
              <p className="text-xs capitalize text-muted-foreground">{integration.category} · {integration.environment}</p>
            </div>
          </div>
          <Badge variant="outline" className={cn("capitalize", statusStyles[integration.status])}>
            {integration.status}
          </Badge>
        </div>
        <p className="mt-3 line-clamp-2 text-xs text-muted-foreground">{integration.description}</p>
        <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
          <div>
            <p className="text-muted-foreground">Requests / mo</p>
            <p className="font-semibold">{integration.requestsThisMonth.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Error rate</p>
            <p className="font-semibold">{integration.errorRate.toFixed(1)}%</p>
          </div>
        </div>
        {integration.lastSyncAt && (
          <p className="mt-2 text-[11px] text-muted-foreground">
            Last sync {formatDistanceToNow(new Date(integration.lastSyncAt), { addSuffix: true })}
          </p>
        )}
        <div className="mt-4 flex gap-2">
          <Button size="sm" variant="outline" className="h-8" onClick={() => onConfigure?.(integration)}>
            Configure
          </Button>
          <Button
            size="sm"
            variant={integration.status === "connected" ? "outline" : "default"}
            className="h-8"
            onClick={() => onToggle?.(integration)}
          >
            {integration.status === "connected" ? "Disconnect" : "Connect"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
