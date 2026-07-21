import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, Edit, Mail, MapPin, MessageSquare, Phone, Sparkles, Tag, Trash2, User, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AudienceAvatar } from "@/components/common/audience-avatar";
import { StatusBadge } from "@/components/common/status-badge";
import { SectionHeader } from "@/components/common/section-header";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { EmptyState } from "@/components/common/empty-state";
import { Timeline, type TimelineItem } from "@/components/common/timeline";
import { PermissionGuard } from "@/components/common/permission-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { audienceService } from "@/services/audience.service";
import { PERMISSIONS } from "@/constants/rbac";

export const Route = createFileRoute("/_authenticated/audience/$id/")({
  head: () => ({ meta: [{ title: "Contact — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: AudienceDetailPage,
});

const EVENT_ICON: Record<string, typeof User> = {
  created: User, updated: Edit, consent: Tag, campaign_delivered: MessageSquare, campaign_opened: Sparkles, tag_added: Tag, group_joined: Users,
};

function AudienceDetailPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [deleteOpen, setDeleteOpen] = useState(false);

  const contactQuery = useQuery({ queryKey: ["audience", id], queryFn: () => audienceService.get(id) });
  const activityQuery = useQuery({ queryKey: ["audience", id, "activity"], queryFn: () => audienceService.activity(id) });

  if (contactQuery.isLoading) return <SkeletonBlock rows={12} />;
  if (contactQuery.isError) return <ErrorState onRetry={() => contactQuery.refetch()} />;
  const contact = contactQuery.data;
  if (!contact) return <EmptyState title="Contact not found" description="It may have been deleted." />;

  const events: TimelineItem[] = (activityQuery.data ?? []).map((e) => ({
    id: e.id,
    title: e.message,
    description: e.actor ? `by ${e.actor}` : undefined,
    at: e.at,
    icon: EVENT_ICON[e.type] ?? User,
    tone: e.type === "campaign_delivered" ? "primary" : e.type === "campaign_opened" ? "accent" : "muted",
  }));

  async function handleDelete() {
    await audienceService.remove(id);
    toast.success("Contact archived");
    qc.invalidateQueries({ queryKey: ["audience"] });
    navigate({ to: "/audience" });
  }

  return (
    <div className="space-y-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="gap-2 text-muted-foreground">
          <Link to="/audience"><ArrowLeft className="h-4 w-4" /> Back to audience</Link>
        </Button>
      </div>

      <SectionHeader
        title={contact.fullName}
        description={contact.occupation ?? "Audience contact"}
        actions={
          <div className="flex gap-2">
            <PermissionGuard anyOf={[PERMISSIONS.AUDIENCE_EDIT]}>
              <Button size="sm" variant="outline" onClick={() => navigate({ to: "/audience/$id/edit", params: { id } })} className="gap-2">
                <Edit className="h-4 w-4" /> Edit
              </Button>
            </PermissionGuard>
            <PermissionGuard anyOf={[PERMISSIONS.AUDIENCE_DELETE]}>
              <Button size="sm" variant="destructive" onClick={() => setDeleteOpen(true)} className="gap-2">
                <Trash2 className="h-4 w-4" /> Archive
              </Button>
            </PermissionGuard>
          </div>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="shadow-card xl:col-span-1">
          <CardContent className="p-6 text-center">
            <AudienceAvatar name={contact.fullName} src={contact.avatarUrl} size="lg" className="mx-auto" />
            <p className="mt-3 text-lg font-semibold">{contact.fullName}</p>
            <p className="text-xs text-muted-foreground">{contact.email}</p>
            <div className="mt-3 flex justify-center"><StatusBadge status={contact.status} /></div>
            {contact.tags.length > 0 && (
              <div className="mt-4 flex flex-wrap justify-center gap-1">
                {contact.tags.map((t) => (
                  <span key={t.id} className="rounded-full px-2 py-0.5 text-[10px] font-medium" style={{ background: `${t.color}1a`, color: t.color }}>
                    {t.name}
                  </span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-card xl:col-span-2">
          <CardHeader><CardTitle className="text-base">Contact information</CardTitle></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2 text-sm">
            <InfoRow icon={Mail} label="Email" value={contact.email} />
            <InfoRow icon={Phone} label="Phone" value={contact.phone} />
            {contact.alternatePhone && <InfoRow icon={Phone} label="Alternate" value={contact.alternatePhone} />}
            <InfoRow icon={MapPin} label="Location" value={`${contact.city}, ${contact.district}, ${contact.state}`} />
            {contact.pincode && <InfoRow icon={MapPin} label="Pincode" value={contact.pincode} />}
            <InfoRow icon={MessageSquare} label="Preferred channel" value={contact.preferredChannel.toUpperCase()} />
            <InfoRow icon={User} label="Preferred language" value={contact.preferredLanguage.toUpperCase()} />
            {contact.gender && <InfoRow icon={User} label="Gender" value={contact.gender} />}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="shadow-card xl:col-span-2">
          <CardHeader><CardTitle className="text-base">Activity timeline</CardTitle></CardHeader>
          <CardContent>
            {activityQuery.isLoading ? <SkeletonBlock rows={4} /> : events.length === 0 ? (
              <EmptyState title="No activity yet" description="Campaign engagement will appear here." />
            ) : <Timeline items={events} />}
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader><CardTitle className="text-base">Organization</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p className="font-medium">{contact.organizationName ?? "Unassigned"}</p>
            {contact.department && <p className="text-muted-foreground">Department · {contact.department}</p>}
            {contact.notes && (
              <>
                <div className="border-t my-3" />
                <p className="text-xs uppercase tracking-wide text-muted-foreground">Notes</p>
                <p>{contact.notes}</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title={`Archive ${contact.fullName}?`}
        description="Archived contacts can be restored within 30 days."
        confirmLabel="Archive"
        destructive
        onConfirm={handleDelete}
      />
    </div>
  );
}

function InfoRow({ icon: Icon, label, value }: { icon: typeof User; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="truncate text-sm font-medium text-foreground">{value}</p>
      </div>
    </div>
  );
}
