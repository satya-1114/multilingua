import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { systemService } from "@/services/system.service";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const Route = createFileRoute("/_authenticated/admin/platform")({
  component: PlatformConfigPage,
});

function PlatformConfigPage() {
  const qc = useQueryClient();
  const config = useQuery({ queryKey: ["admin", "config"], queryFn: () => systemService.config() });

  async function update(sectionId: string, key: string, value: string | number | boolean) {
    await systemService.updateConfig(sectionId, key, value);
    qc.invalidateQueries({ queryKey: ["admin", "config"] });
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {(config.data ?? []).map((section) => (
        <Card key={section.id} className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">{section.label}</CardTitle>
            <p className="text-xs text-muted-foreground">{section.description}</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {section.entries.map((e) => (
              <div key={e.key} className="grid grid-cols-2 items-center gap-3">
                <div>
                  <Label className="text-xs">{e.label}</Label>
                  <p className="font-mono text-[10px] text-muted-foreground">{e.key}</p>
                </div>
                {e.kind === "boolean" && (
                  <div className="justify-self-end">
                    <Switch checked={Boolean(e.value)} onCheckedChange={(v) => update(section.id, e.key, v)} />
                  </div>
                )}
                {e.kind === "text" && (
                  <Input defaultValue={String(e.value)} onBlur={(ev) => update(section.id, e.key, ev.target.value)} />
                )}
                {e.kind === "number" && (
                  <Input
                    type="number"
                    defaultValue={Number(e.value)}
                    onBlur={(ev) => update(section.id, e.key, Number(ev.target.value))}
                  />
                )}
                {e.kind === "select" && (
                  <Select defaultValue={String(e.value)} onValueChange={(v) => update(section.id, e.key, v)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {(e.options ?? []).map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
