import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RetryPolicyEditor } from "@/components/common/retry-policy-editor";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ChannelBadge } from "@/components/common/channel-badge";
import { retryPolicyService } from "@/services/retry-policy.service";
import { toast } from "sonner";
import { Plus, Trash2, Pencil } from "lucide-react";
import type { RetryPolicy } from "@/types/retry-policy";

export const Route = createFileRoute("/_authenticated/communication/retry-policies")({
  component: RetryPoliciesPage,
});

function RetryPoliciesPage() {
  const q = useQuery({ queryKey: ["retry-policies"], queryFn: () => retryPolicyService.list() });
  const [editing, setEditing] = useState<RetryPolicy | "new" | null>(null);
  const policies = q.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <Button onClick={() => setEditing("new")}><Plus className="mr-2 h-4 w-4" />New policy</Button>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {policies.map((p) => (
          <Card key={p.id} className="shadow-card">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <div><CardTitle className="text-base">{p.name}</CardTitle>
                  {p.description && <p className="mt-1 text-xs text-muted-foreground">{p.description}</p>}
                </div>
                <div className="flex gap-1">
                  <Button size="icon" variant="ghost" onClick={() => setEditing(p)}><Pencil className="h-4 w-4" /></Button>
                  <Button size="icon" variant="ghost" disabled={p.isDefault} onClick={async () => { await retryPolicyService.remove(p.id); toast.success("Removed"); q.refetch(); }}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <dl className="grid grid-cols-3 gap-2 text-xs">
                <div><dt className="text-muted-foreground">Attempts</dt><dd className="font-medium">{p.maxAttempts}</dd></div>
                <div><dt className="text-muted-foreground">Interval</dt><dd className="font-medium">{p.intervalSeconds}s</dd></div>
                <div><dt className="text-muted-foreground">Backoff</dt><dd className="font-medium">{p.backoff}</dd></div>
              </dl>
              <div className="flex flex-wrap gap-1">
                {p.channels.map((c) => <ChannelBadge key={c} channel={c} />)}
              </div>
              <div className="flex flex-wrap gap-1 text-[11px] text-muted-foreground">
                {p.retryOn.map((r) => <span key={r} className="rounded-full bg-muted px-2 py-0.5">{r.replace(/_/g, " ")}</span>)}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent className="max-w-4xl">
          <DialogHeader><DialogTitle>{editing === "new" ? "New retry policy" : `Edit · ${editing && typeof editing !== "string" ? editing.name : ""}`}</DialogTitle></DialogHeader>
          <RetryPolicyEditor
            initial={editing && editing !== "new" ? editing : undefined}
            onCancel={() => setEditing(null)}
            onSubmit={async (v) => {
              if (editing && editing !== "new") await retryPolicyService.update(editing.id, v);
              else await retryPolicyService.create(v);
              toast.success("Policy saved");
              setEditing(null);
              q.refetch();
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
