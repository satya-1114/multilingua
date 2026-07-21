import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Monitor, Smartphone } from "lucide-react";
import { securityService } from "@/services/security.service";

export const Route = createFileRoute("/_authenticated/security/sessions")({
  component: SessionsPage,
});

function SessionsPage() {
  const qc = useQueryClient();
  const sessions = useQuery({ queryKey: ["sec", "sessions"], queryFn: () => securityService.sessions() });
  const revoke = useMutation({
    mutationFn: (id: string) => securityService.revokeSession(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sec", "sessions"] }),
  });

  return (
    <div className="space-y-3">
      {(sessions.data ?? []).map((s) => {
        const isMobile = s.device.toLowerCase().includes("iphone") || s.device.toLowerCase().includes("android");
        const Icon = isMobile ? Smartphone : Monitor;
        return (
          <Card key={s.id} className="shadow-card">
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold">{s.device}</p>
                    {s.current && <Badge>Current</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {s.browser} · {s.location} · {s.ip}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    Signed in {formatDistanceToNow(new Date(s.createdAt), { addSuffix: true })} · Active {formatDistanceToNow(new Date(s.lastActiveAt), { addSuffix: true })}
                  </p>
                </div>
              </div>
              {!s.current && (
                <Button size="sm" variant="outline" onClick={() => revoke.mutate(s.id)}>Revoke</Button>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
