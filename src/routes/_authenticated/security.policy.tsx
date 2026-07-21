import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { PermissionMatrix } from "@/components/common/permission-matrix";
import { securityService } from "@/services/security.service";

export const Route = createFileRoute("/_authenticated/security/policy")({
  component: PolicyPage,
});

function PolicyPage() {
  const qc = useQueryClient();
  const policy = useQuery({ queryKey: ["sec", "policy"], queryFn: () => securityService.policy() });
  const update = useMutation({
    mutationFn: (patch: Parameters<typeof securityService.updatePolicy>[0]) => securityService.updatePolicy(patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sec", "policy"] }),
  });
  const p = policy.data;

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader><CardTitle className="text-base">Password policy</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <Label className="text-xs uppercase text-muted-foreground">Minimum length</Label>
            <Input type="number" defaultValue={p?.minLength ?? 12} onBlur={(e) => update.mutate({ minLength: Number(e.target.value) })} />
          </div>
          <div>
            <Label className="text-xs uppercase text-muted-foreground">Rotation days</Label>
            <Input type="number" defaultValue={p?.rotationDays ?? 90} onBlur={(e) => update.mutate({ rotationDays: Number(e.target.value) })} />
          </div>
          <div>
            <Label className="text-xs uppercase text-muted-foreground">History depth</Label>
            <Input type="number" defaultValue={p?.historyDepth ?? 5} onBlur={(e) => update.mutate({ historyDepth: Number(e.target.value) })} />
          </div>
          <div className="space-y-2">
            <SwitchRow label="Require uppercase" defaultChecked={p?.requireUppercase} onChange={(v) => update.mutate({ requireUppercase: v })} />
            <SwitchRow label="Require number" defaultChecked={p?.requireNumber} onChange={(v) => update.mutate({ requireNumber: v })} />
            <SwitchRow label="Require symbol" defaultChecked={p?.requireSymbol} onChange={(v) => update.mutate({ requireSymbol: v })} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Permission matrix</CardTitle></CardHeader>
        <CardContent><PermissionMatrix /></CardContent>
      </Card>
    </div>
  );
}

function SwitchRow({ label, defaultChecked, onChange }: { label: string; defaultChecked?: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between rounded-lg border px-3 py-2">
      <span className="text-sm">{label}</span>
      <Switch defaultChecked={defaultChecked} onCheckedChange={onChange} />
    </div>
  );
}
