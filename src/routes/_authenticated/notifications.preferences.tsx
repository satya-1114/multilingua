import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { communicationService } from "@/services/communication.service";
import { toast } from "sonner";
import type { NotificationPreferences, NotificationChannelPreference } from "@/types/communication";

export const Route = createFileRoute("/_authenticated/notifications/preferences")({
  head: () => ({ meta: [{ title: "Notification preferences" }, { name: "robots", content: "noindex" }] }),
  component: PreferencesPage,
});

const CHANNELS: Array<{ key: keyof Pick<NotificationPreferences, "email" | "sms" | "push" | "inApp">; label: string; description: string }> = [
  { key: "email", label: "Email", description: "Long-form updates and digests." },
  { key: "sms", label: "SMS", description: "High-priority text alerts." },
  { key: "push", label: "Push", description: "Mobile push notifications." },
  { key: "inApp", label: "In-app", description: "Notifications inside the platform." },
];

const LANGUAGES = ["English", "Hindi", "Tamil", "Telugu", "Bengali", "Marathi"];

function PreferencesPage() {
  const q = useQuery({ queryKey: ["preferences"], queryFn: () => communicationService.getPreferences() });
  const [state, setState] = useState<NotificationPreferences | null>(null);
  useEffect(() => { if (q.data) setState(q.data); }, [q.data]);

  if (!state) return <p className="text-sm text-muted-foreground">Loading…</p>;

  const patch = (key: keyof NotificationPreferences, value: unknown) =>
    setState({ ...state, [key]: value });

  const patchChannel = (key: "email" | "sms" | "push" | "inApp", patchObj: Partial<NotificationChannelPreference>) =>
    setState({ ...state, [key]: { ...state[key], ...patchObj } });

  return (
    <div className="space-y-5">

        <Button asChild variant="ghost" size="sm"><Link to="/notifications"><ArrowLeft className="mr-2 h-4 w-4" />Back to notifications</Link></Button>
        <SectionHeader title="Notification preferences" description="Choose how and when this account receives notifications." />

        <div className="grid gap-4 lg:grid-cols-2">
          {CHANNELS.map(({ key, label, description }) => {
            const ch = state[key];
            return (
              <Card key={key} className="shadow-card">
                <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                  <div>
                    <CardTitle className="text-base">{label}</CardTitle>
                    <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
                  </div>
                  <Switch checked={ch.enabled} onCheckedChange={(v) => patchChannel(key, { enabled: v })} />
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid gap-2">
                    <Label>Digest</Label>
                    <Select value={ch.digest} onValueChange={(v) => patchChannel(key, { digest: v as NotificationChannelPreference["digest"] })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="off">Off</SelectItem>
                        <SelectItem value="daily">Daily</SelectItem>
                        <SelectItem value="weekly">Weekly</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="rounded-lg border p-3">
                    <div className="flex items-center justify-between">
                      <Label>Quiet hours</Label>
                      <Switch checked={ch.quietHours.enabled} onCheckedChange={(v) => patchChannel(key, { quietHours: { ...ch.quietHours, enabled: v } })} />
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <Input type="time" value={ch.quietHours.start} onChange={(e) => patchChannel(key, { quietHours: { ...ch.quietHours, start: e.target.value } })} />
                      <Input type="time" value={ch.quietHours.end} onChange={(e) => patchChannel(key, { quietHours: { ...ch.quietHours, end: e.target.value } })} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Global preferences</CardTitle></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <div className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-amber-500" /><p className="text-sm font-medium">Emergency override</p></div>
                <p className="text-xs text-muted-foreground">Always deliver critical alerts, bypassing quiet hours.</p>
              </div>
              <Switch checked={state.emergencyOverride} onCheckedChange={(v) => patch("emergencyOverride", v)} />
            </div>
            <div className="grid gap-2">
              <Label>Preferred language</Label>
              <Select value={state.language} onValueChange={(v) => patch("language", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{LANGUAGES.map((l) => <SelectItem key={l} value={l}>{l}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button onClick={async () => {
            await communicationService.updatePreferences(state);
            toast.success("Preferences saved");
          }}>Save preferences</Button>
        </div>
      </div>
  );
}
