import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SectionHeader } from "@/components/common/section-header";
import { FormField } from "@/components/common/form-field";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PermissionGuard } from "@/components/common/permission-guard";
import { useTheme } from "@/contexts/theme-context";
import { organizationService } from "@/services/organization.service";
import { PERMISSIONS } from "@/constants/rbac";

export const Route = createFileRoute("/_authenticated/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: SettingsPage,
});

const timezones = ["UTC", "Asia/Kolkata", "Europe/London", "America/New_York", "America/Los_Angeles", "Asia/Singapore"];
const languages = [
  { value: "en", label: "English" },
  { value: "en-IN", label: "English (India)" },
  { value: "hi", label: "Hindi" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "ar", label: "Arabic" },
];

function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [dangerOpen, setDangerOpen] = useState(false);
  const [notif, setNotif] = useState({ email: true, push: true, digest: false, announcements: true });
  const orgQuery = useQuery({ queryKey: ["organization", "current"], queryFn: () => organizationService.getCurrent() });

  const org = orgQuery.data;

  async function saveOrganization(patch: Record<string, string>) {
    if (!org) return;
    await organizationService.update(org.id, patch);
    await orgQuery.refetch();
    toast.success("Organization updated");
  }

  return (
    <div className="space-y-6">
      <SectionHeader title="Settings" description="Manage workspace, preferences, and integrations." />

      <PermissionGuard anyOf={[PERMISSIONS.ORG_VIEW]}>
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">Organization</CardTitle>
            <CardDescription>Details shared across your workspace.</CardDescription>
          </CardHeader>
          <CardContent>
            {org && (
              <form
                className="grid gap-4 sm:grid-cols-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = new FormData(e.currentTarget);
                  void saveOrganization({
                    name: String(form.get("name") ?? org.name),
                    website: String(form.get("website") ?? org.website),
                    address: String(form.get("address") ?? org.address),
                  });
                }}
              >
                <FormField id="org-name" name="name" label="Organization name" defaultValue={org.name} />
                <FormField id="org-type" label="Organization type" defaultValue={org.type} disabled />
                <FormField id="org-website" name="website" label="Website" defaultValue={org.website} />
                <FormField id="org-address" name="address" label="Address" defaultValue={org.address} />
                <div className="sm:col-span-2 flex justify-end">
                  <PermissionGuard
                    anyOf={[PERMISSIONS.ORG_MANAGE]}
                    fallback={
                      <Button type="button" disabled>
                        Contact an admin to edit
                      </Button>
                    }
                  >
                    <Button type="submit">Save changes</Button>
                  </PermissionGuard>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </PermissionGuard>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">Appearance</CardTitle>
            <CardDescription>Choose how the platform looks on this device.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              {(["light", "dark", "system"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTheme(t)}
                  className={`rounded-lg border p-3 text-sm font-medium capitalize transition-colors ${
                    theme === t
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">Language & timezone</CardTitle>
            <CardDescription>These affect dates, numbers, and communications.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="lang">Interface language</Label>
              <Select defaultValue="en">
                <SelectTrigger id="lang"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {languages.map((l) => (
                    <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tz">Timezone</Label>
              <Select defaultValue="UTC">
                <SelectTrigger id="tz"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {timezones.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle className="text-base">Notifications</CardTitle>
          <CardDescription>Decide what we notify you about, and where.</CardDescription>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          {[
            { key: "email", label: "Email notifications", helper: "Delivery reports and campaign updates." },
            { key: "push", label: "In-app alerts", helper: "Real-time notifications inside the platform." },
            { key: "digest", label: "Weekly digest", helper: "A summary of the week's activity every Monday." },
            { key: "announcements", label: "Product announcements", helper: "New features and improvements." },
          ].map((row) => (
            <div key={row.key} className="flex items-start justify-between gap-4 py-3">
              <div>
                <p className="text-sm font-medium text-foreground">{row.label}</p>
                <p className="text-xs text-muted-foreground">{row.helper}</p>
              </div>
              <Switch
                checked={notif[row.key as keyof typeof notif]}
                onCheckedChange={(v) => setNotif((s) => ({ ...s, [row.key]: v }))}
                aria-label={row.label}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">Security</CardTitle>
            <CardDescription>Session controls for your account.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span>Sign out inactive sessions after 30 minutes</span>
              <Switch defaultChecked aria-label="Idle session timeout" />
            </div>
            <div className="flex items-center justify-between">
              <span>Restrict sign-ins to trusted IP addresses</span>
              <Switch aria-label="IP restrictions" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">API keys</CardTitle>
            <CardDescription>Programmatic access for integrations.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Personal and workspace API keys will appear here once available. Reach out to your
              administrator to request access.
            </p>
            <Button variant="outline" size="sm" className="mt-3" disabled>
              Generate key
            </Button>
          </CardContent>
        </Card>
      </div>

      <PermissionGuard anyOf={[PERMISSIONS.ORG_MANAGE]}>
        <Card className="border-destructive/40 bg-destructive/[.03] shadow-card">
          <CardHeader>
            <CardTitle className="text-base text-destructive">Danger zone</CardTitle>
            <CardDescription>Irreversible actions. Please proceed with caution.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-foreground">Delete workspace</p>
              <p className="text-xs text-muted-foreground">
                Permanently remove this workspace, all campaigns, and all associated data.
              </p>
            </div>
            <Button variant="destructive" size="sm" className="gap-2" onClick={() => setDangerOpen(true)}>
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </Button>
          </CardContent>
        </Card>
      </PermissionGuard>

      <ConfirmDialog
        open={dangerOpen}
        onOpenChange={setDangerOpen}
        title="Delete this workspace?"
        description="This action cannot be undone. All campaigns, audiences, and analytics for this workspace will be permanently removed."
        confirmLabel="Yes, delete workspace"
        destructive
        onConfirm={() => {
          setDangerOpen(false);
          toast.success("Workspace deletion requested — an admin will confirm within 24 hours.");
        }}
      />
    </div>
  );
}
