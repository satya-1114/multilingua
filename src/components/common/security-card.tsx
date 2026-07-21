import { formatDistanceToNow } from "date-fns";
import { AlertTriangle, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SecurityAlert } from "@/types/security";

const sevMap: Record<SecurityAlert["severity"], { color: string; label: string }> = {
  low: { color: "bg-muted text-muted-foreground", label: "Low" },
  medium: { color: "bg-warning/10 text-warning", label: "Medium" },
  high: { color: "bg-destructive/10 text-destructive", label: "High" },
  critical: { color: "bg-destructive text-destructive-foreground", label: "Critical" },
};

const statusIcon = {
  open: ShieldAlert,
  acknowledged: ShieldQuestion,
  resolved: ShieldCheck,
} as const;

interface SecurityCardProps {
  alert: SecurityAlert;
  onAcknowledge?: (a: SecurityAlert) => void;
  onResolve?: (a: SecurityAlert) => void;
}

export function SecurityCard({ alert, onAcknowledge, onResolve }: SecurityCardProps) {
  const Icon = statusIcon[alert.status];
  const sev = sevMap[alert.severity];
  return (
    <Card className="shadow-card">
      <CardContent className="p-5">
        <div className="flex items-start gap-3">
          <div className={cn("mt-0.5 flex h-9 w-9 items-center justify-center rounded-lg", sev.color)}>
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold">{alert.title}</p>
              <Badge variant="outline" className={cn(sev.color)}>{sev.label}</Badge>
              <Badge variant="outline" className="capitalize"><Icon className="mr-1 h-3 w-3" />{alert.status}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{alert.description}</p>
            <p className="mt-2 text-[11px] text-muted-foreground">
              {formatDistanceToNow(new Date(alert.at), { addSuffix: true })}
            </p>
          </div>
        </div>
        {alert.status !== "resolved" && (
          <div className="mt-3 flex gap-2">
            {alert.status === "open" && (
              <Button size="sm" variant="outline" className="h-8" onClick={() => onAcknowledge?.(alert)}>
                Acknowledge
              </Button>
            )}
            <Button size="sm" variant="outline" className="h-8" onClick={() => onResolve?.(alert)}>
              Mark resolved
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
