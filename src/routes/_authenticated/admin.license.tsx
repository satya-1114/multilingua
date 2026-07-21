import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { systemService } from "@/services/system.service";

export const Route = createFileRoute("/_authenticated/admin/license")({
  component: LicensePage,
});

function LicensePage() {
  const license = useQuery({ queryKey: ["admin", "license"], queryFn: () => systemService.license() });
  const l = license.data;
  const pct = l ? (l.seatsUsed / l.seats) * 100 : 0;
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Card className="shadow-card">
        <CardHeader>
          <CardTitle className="text-base">Current plan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-2xl font-semibold">{l?.plan ?? "—"}</p>
            <Badge>Active</Badge>
          </div>
          <p className="text-xs text-muted-foreground">Contract {l?.contractId}</p>
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Seats</span>
              <span className="font-mono">{l?.seatsUsed} / {l?.seats}</span>
            </div>
            <Progress value={pct} className="mt-1 h-1.5" />
          </div>
          <p className="text-xs text-muted-foreground">Renews on {l ? format(new Date(l.renewsOn), "PPP") : "—"}</p>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Included features</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            {(l?.features ?? []).map((f) => (
              <li key={f} className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" />
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
