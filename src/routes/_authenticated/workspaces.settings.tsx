import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { workspaceService } from "@/services/workspace.service";

export const Route = createFileRoute("/_authenticated/workspaces/settings")({
  head: () => ({ meta: [{ title: "Workspace settings" }, { name: "robots", content: "noindex" }] }),
  component: WorkspaceSettingsPage,
});

function WorkspaceSettingsPage() {
  const current = useQuery({ queryKey: ["workspace", "current"], queryFn: () => workspaceService.current() });
  const w = current.data;
  const [primaryColor, setPrimaryColor] = useState("#2563EB");

  return (
    <div className="space-y-5">
        <SectionHeader title="Workspace settings" description={w?.name ? `Configure ${w.name}` : "Loading workspace…"} />
        <Tabs defaultValue="general">
          <TabsList className="flex-wrap">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="branding">Branding</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="users">Users</TabsTrigger>
            <TabsTrigger value="communication">Communication</TabsTrigger>
            <TabsTrigger value="storage">Storage &amp; API</TabsTrigger>
            <TabsTrigger value="audit">Audit</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="mt-4">
            <Card>
              <CardHeader><CardTitle className="text-base">General</CardTitle></CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Field label="Workspace name" defaultValue={w?.name ?? ""} />
                <Field label="Slug" defaultValue={w?.slug ?? ""} />
                <Field label="Timezone" defaultValue={w?.timezone ?? "Asia/Kolkata"} />
                <Field label="Region" defaultValue={w?.region ?? "IN"} />
                <div className="md:col-span-2">
                  <Label className="text-xs uppercase text-muted-foreground">Supported languages</Label>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {(w?.languages ?? []).map((l) => <Badge key={l} variant="outline" className="uppercase">{l}</Badge>)}
                  </div>
                </div>
                <div><Button>Save changes</Button></div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="branding" className="mt-4">
            <Card>
              <CardHeader><CardTitle className="text-base">Branding</CardTitle></CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-xs uppercase text-muted-foreground">Primary color</Label>
                  <div className="mt-2 flex items-center gap-3">
                    <input type="color" value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className="h-9 w-16 cursor-pointer rounded border" />
                    <Input value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} className="w-32 font-mono" />
                  </div>
                </div>
                <Field label="Support email" defaultValue="support@dept.gov.in" />
                <Field label="Logo URL" placeholder="https://…" />
                <Field label="Email footer" defaultValue="Sent from the multilingual communication platform." />
                <div><Button>Save branding</Button></div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security" className="mt-4">
            <Card>
              <CardHeader><CardTitle className="text-base">Security</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <SwitchRow label="Enforce 2FA for all members" defaultChecked />
                <SwitchRow label="Require SSO sign-in" />
                <SwitchRow label="Restrict access to allow-listed IPs" />
                <SwitchRow label="Session activity tracking" defaultChecked />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="users" className="mt-4">
            <Card>
              <CardHeader><CardTitle className="text-base">Users</CardTitle></CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Manage members and roles from the <a href="/organizations" className="text-primary underline">organization directory</a>.
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="communication" className="mt-4">
            <Card>
              <CardHeader><CardTitle className="text-base">Communication defaults</CardTitle></CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Field label="Default sender name" defaultValue={w?.name ?? ""} />
                <Field label="Default from email" defaultValue="no-reply@dept.gov.in" />
                <Field label="SMS sender ID" defaultValue="GOVMLT" />
                <Field label="WhatsApp business ID" defaultValue="wba-2941" />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="storage" className="mt-4">
            <Card>
              <CardHeader><CardTitle className="text-base">Storage &amp; API usage</CardTitle></CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <MetricLine label="Storage used" value={`${w?.storageUsedGb.toFixed(1) ?? 0} GB / ${w?.storageQuotaGb ?? 0} GB`} />
                <MetricLine label="API calls this month" value={`${(w?.apiUsedThisMonth ?? 0).toLocaleString()} / ${(w?.apiQuotaMonthly ?? 0).toLocaleString()}`} />
                <MetricLine label="Seats used" value={`${w?.memberCount ?? 0}`} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="audit" className="mt-4">
            <Card>
              <CardHeader><CardTitle className="text-base">Audit</CardTitle></CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Detailed audit trail is available in the <a href="/audit-logs" className="text-primary underline">audit log viewer</a>.
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
  );
}

function Field({ label, defaultValue, placeholder }: { label: string; defaultValue?: string; placeholder?: string }) {
  return (
    <div>
      <Label className="text-xs uppercase text-muted-foreground">{label}</Label>
      <Input defaultValue={defaultValue} placeholder={placeholder} className="mt-1" />
    </div>
  );
}

function SwitchRow({ label, defaultChecked }: { label: string; defaultChecked?: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border px-3 py-2">
      <span className="text-sm">{label}</span>
      <Switch defaultChecked={defaultChecked} />
    </div>
  );
}

function MetricLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
