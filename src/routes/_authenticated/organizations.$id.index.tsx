import { useState } from "react";
import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Building2, Edit, Globe, Mail, MapPin, Phone, Trash2, Users, Megaphone } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { SectionHeader } from "@/components/common/section-header";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { EmptyState } from "@/components/common/empty-state";
import { StatusBadge } from "@/components/common/status-badge";
import { PermissionGuard } from "@/components/common/permission-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { organizationService } from "@/services/organization.service";
import { auditService } from "@/services/audit.service";
import { PERMISSIONS } from "@/constants/rbac";

export const Route = createFileRoute("/_authenticated/organizations/$id/")({
  head: () => ({ meta: [{ title: "Organization — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: OrganizationDetailPage,
});

function OrganizationDetailPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const orgQuery = useQuery({ queryKey: ["organizations", id], queryFn: () => organizationService.get(id) });
  const auditQuery = useQuery({
    queryKey: ["organizations", id, "audit"],
    queryFn: () => auditService.list({ module: ["organization"], pageSize: 10 }),
  });

  if (orgQuery.isLoading) return <SkeletonBlock rows={10} />;
  const org = orgQuery.data;
  if (!org) return <EmptyState title="Organization not found" />;

  async function handleDelete() {
    await organizationService.remove(id);
    toast.success("Organization deleted");
    qc.invalidateQueries({ queryKey: ["organizations"] });
    navigate({ to: "/organizations" });
  }

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="gap-2 text-muted-foreground">
        <Link to="/organizations"><ArrowLeft className="h-4 w-4" /> All organizations</Link>
      </Button>

      <SectionHeader
        title={org.name}
        description={`${org.type} · ${org.city}, ${org.state}`}
        actions={
          <div className="flex gap-2">
            <PermissionGuard anyOf={[PERMISSIONS.ORG_EDIT]}>
              <Button size="sm" variant="outline" onClick={() => navigate({ to: "/organizations/$id/edit", params: { id } })} className="gap-2">
                <Edit className="h-4 w-4" /> Edit
              </Button>
            </PermissionGuard>
            <PermissionGuard anyOf={[PERMISSIONS.ORG_DELETE]}>
              <Button size="sm" variant="destructive" onClick={() => setDeleteOpen(true)} className="gap-2">
                <Trash2 className="h-4 w-4" /> Delete
              </Button>
            </PermissionGuard>
          </div>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="shadow-card xl:col-span-1">
          <CardContent className="p-6">
            <div className="flex items-start gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Building2 className="h-6 w-6" />
              </div>
              <div className="min-w-0">
                <p className="truncate font-semibold">{org.name}</p>
                <p className="text-xs text-muted-foreground">{org.type}</p>
                <div className="mt-2"><StatusBadge status={org.status} /></div>
              </div>
            </div>
            <dl className="mt-5 space-y-3 text-sm">
              {org.website && <Row icon={Globe} label="Website" value={org.website} />}
              <Row icon={Mail} label="Email" value={org.email} />
              <Row icon={Phone} label="Phone" value={org.phone} />
              <Row icon={MapPin} label="Address" value={`${org.address}, ${org.city}, ${org.state} ${org.pincode ?? ""}`} />
            </dl>
          </CardContent>
        </Card>

        <div className="xl:col-span-2 space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <MiniStat icon={Users} label="Users" value={org.userCount} />
            <MiniStat icon={Users} label="Audience" value={org.audienceCount.toLocaleString()} />
            <MiniStat icon={Megaphone} label="Campaigns" value={org.campaignCount} />
          </div>

          <Card className="shadow-card">
            <CardContent className="p-0">
              <Tabs defaultValue="overview">
                <TabsList className="w-full justify-start rounded-none border-b bg-transparent p-0">
                  <TabsTrigger value="overview" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">Overview</TabsTrigger>
                  <TabsTrigger value="users" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">Users</TabsTrigger>
                  <TabsTrigger value="campaigns" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">Campaigns</TabsTrigger>
                  <TabsTrigger value="activity" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary">Activity</TabsTrigger>
                </TabsList>
                <TabsContent value="overview" className="p-5 space-y-4 text-sm">
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Primary administrator</p>
                    <p className="mt-1 font-medium">{org.primaryAdminName ?? "—"}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Timezone</p>
                    <p className="mt-1 font-medium">{org.timezone}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Languages</p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {org.languages.map((l) => (
                        <span key={l} className="rounded-full bg-muted px-2 py-0.5 text-xs uppercase">{l}</span>
                      ))}
                    </div>
                  </div>
                </TabsContent>
                <TabsContent value="users" className="p-5">
                  <EmptyState title="User management coming soon" description="Assign roles and manage member access." />
                </TabsContent>
                <TabsContent value="campaigns" className="p-5">
                  <EmptyState title="Campaigns coming soon" description="Campaign listing will appear here." />
                </TabsContent>
                <TabsContent value="activity" className="p-5">
                  {auditQuery.isLoading ? (
                    <SkeletonBlock rows={4} />
                  ) : (auditQuery.data?.items ?? []).length === 0 ? (
                    <EmptyState title="No recent activity" />
                  ) : (
                    <ul className="divide-y">
                      {(auditQuery.data?.items ?? []).map((l) => (
                        <li key={l.id} className="flex items-center justify-between py-2 text-sm">
                          <span className="capitalize">{l.action} · {l.entityLabel}</span>
                          <span className="text-xs text-muted-foreground">{new Date(l.createdAt).toLocaleString()}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={`Delete ${org.name}?`}
        description="This will remove the organization and unlink its data."
        destructive
        confirmLabel="Delete"
        onConfirm={handleDelete}
      />
    </div>
  );
}

function Row({ icon: Icon, label, value }: { icon: typeof Building2; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <Icon className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm truncate">{value}</p>
      </div>
    </div>
  );
}

function MiniStat({ icon: Icon, label, value }: { icon: typeof Users; label: string; value: number | string }) {
  return (
    <Card className="shadow-card">
      <CardContent className="p-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Icon className="h-4 w-4" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
