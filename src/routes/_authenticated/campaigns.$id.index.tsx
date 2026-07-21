import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  Copy,
  Edit3,
  Play,
  Send,
  Square,
  PauseCircle,
  MessageSquarePlus,
  Pin,
  ArrowLeft,
  Activity,
} from "lucide-react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import { SectionHeader } from "@/components/common/section-header";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { CampaignStatusBadge } from "@/components/common/campaign-status-badge";
import { WorkflowStepper } from "@/components/common/workflow-stepper";
import { ApprovalTimeline } from "@/components/common/approval-timeline";
import { ApprovalBadge } from "@/components/common/approval-badge";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Timeline } from "@/components/common/timeline";
import { CampaignQrPanel } from "@/components/common/campaign-qr-panel";
import { MultilingualPanel } from "@/components/common/multilingual-panel";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { campaignService } from "@/services/campaign.service";
import { approvalService } from "@/services/approval.service";
import { templateService } from "@/services/template.service";
import { useAuth } from "@/contexts/auth-context";
import { PERMISSIONS } from "@/constants/rbac";
import type { CampaignStatus } from "@/types/campaign";
import { CAMPAIGN_STATUS_META } from "@/constants/campaign";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/campaigns/$id/")({
  head: () => ({
    meta: [
      { title: "Campaign details — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: CampaignDetailPage,
});

function CampaignDetailPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const cq = useQuery({ queryKey: ["campaign", id], queryFn: () => campaignService.get(id) });
  const [noteBody, setNoteBody] = useState("");
  const [confirm, setConfirm] = useState<null | { title: string; action: () => Promise<void>; destructive?: boolean }>(null);

  const tplQ = useQuery({
    queryKey: ["template", cq.data?.templateId],
    queryFn: () => templateService.get(cq.data!.templateId!),
    enabled: !!cq.data?.templateId,
  });

  if (cq.isLoading) return <SkeletonBlock rows={8} />;
  if (cq.isError || !cq.data) return <ErrorState onRetry={() => cq.refetch()} />;
  const c = cq.data;

  const actor = { id: user?.id ?? "user-1", name: user?.fullName ?? "You" };
  const latestApproval = c.approvals[c.approvals.length - 1];

  async function invalidate() {
    await qc.invalidateQueries({ queryKey: ["campaign", id] });
    await qc.invalidateQueries({ queryKey: ["campaigns"] });
  }

  async function transition(to: CampaignStatus, message: string) {
    await campaignService.setStatus(id, to, actor.name);
    toast.success(message);
    invalidate();
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title={c.name}
        description={c.description ?? ""}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate({ to: "/campaigns" })} className="gap-1.5">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <PermissionGuard anyOf={[PERMISSIONS.CAMPAIGN_EDIT]}>
              <Button variant="outline" size="sm" onClick={() => navigate({ to: "/campaigns/$id/edit", params: { id } })} className="gap-1.5">
                <Edit3 className="h-4 w-4" /> Edit
              </Button>
            </PermissionGuard>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={async () => {
                const dup = await campaignService.duplicate(id);
                toast.success("Campaign duplicated");
                navigate({ to: "/campaigns/$id", params: { id: dup.id } });
                invalidate();
              }}
            >
              <Copy className="h-4 w-4" /> Duplicate
            </Button>
            {c.status === "draft" && (
              <PermissionGuard anyOf={[PERMISSIONS.CAMPAIGN_LAUNCH, PERMISSIONS.APPROVAL_ACT]}>
                <Button size="sm" className="gap-1.5" onClick={async () => { await approvalService.submit(id, actor); toast.success("Submitted for approval"); invalidate(); }}>
                  <Send className="h-4 w-4" /> Submit for approval
                </Button>
              </PermissionGuard>
            )}
            {(c.status === "approved" || c.status === "scheduled") && (
              <PermissionGuard anyOf={[PERMISSIONS.CAMPAIGN_LAUNCH]}>
                <Button size="sm" className="gap-1.5" onClick={() => transition("running", "Campaign launched")}>
                  <Play className="h-4 w-4" /> Launch
                </Button>
              </PermissionGuard>
            )}
            {c.status === "running" && (
              <>
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => transition("completed", "Marked as completed")}>
                  <Square className="h-4 w-4" /> Complete
                </Button>
                <Button size="sm" variant="destructive" className="gap-1.5" onClick={() => setConfirm({ title: "Cancel campaign?", action: () => transition("cancelled", "Campaign cancelled"), destructive: true })}>
                  <PauseCircle className="h-4 w-4" /> Cancel
                </Button>
              </>
            )}
            {["completed", "cancelled", "failed"].includes(c.status) && (
              <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setConfirm({ title: "Archive this campaign?", action: () => transition("archived", "Campaign archived") })}>
                <Archive className="h-4 w-4" /> Archive
              </Button>
            )}
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <span className="font-mono text-xs">{c.code}</span>
        <CampaignStatusBadge status={c.status} />
        {latestApproval && <ApprovalBadge status={latestApproval.status} />}
        <span className="text-xs">Owner: <span className="font-medium text-foreground">{c.ownerName}</span></span>
        <span className="text-xs">Organization: <span className="font-medium text-foreground">{c.organizationName}</span></span>
        <span className="ml-auto text-xs">Updated {formatDistanceToNow(new Date(c.updatedAt), { addSuffix: true })}</span>
      </div>

      <WorkflowStepper status={c.status} />

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="audience">Audience</TabsTrigger>
          <TabsTrigger value="content">Communication</TabsTrigger>
          <TabsTrigger value="qr">QR Code</TabsTrigger>
          <TabsTrigger value="translations">Translations</TabsTrigger>
          <TabsTrigger value="approvals">Approvals</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
        </TabsList>


        <TabsContent value="overview">
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2 shadow-card">
              <CardHeader className="pb-2"><CardTitle className="text-base">Information</CardTitle></CardHeader>
              <CardContent className="grid gap-3 text-sm md:grid-cols-2">
                <Info label="Type" value={<span className="capitalize">{c.type.replace(/_/g, " ")}</span>} />
                <Info label="Category" value={<span className="capitalize">{c.category}</span>} />
                <Info label="Priority" value={<span className="capitalize">{c.priority}</span>} />
                <Info label="Visibility" value={<span className="capitalize">{c.visibility}</span>} />
                <Info label="Department" value={c.department ?? "—"} />
                <Info label="Estimated reach" value={c.estimatedReach.toLocaleString()} />
                <Info label="Languages" value={c.languages.map((l) => l.toUpperCase()).join(", ")} />
                <Info label="Tags" value={c.tags.join(", ") || "—"} />
                <Info label="Objective" value={c.objective ?? "—"} className="md:col-span-2" />
              </CardContent>
            </Card>
            <Card className="shadow-card">
              <CardHeader className="pb-2"><CardTitle className="text-base">Schedule</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                <Info label="Mode" value={<span className="capitalize">{c.schedule.mode.replace("_", " ")}</span>} />
                <Info label="Timezone" value={c.schedule.timezone} />
                <Info label="Starts" value={c.schedule.startAt ? new Date(c.schedule.startAt).toLocaleString() : "—"} />
                <Info label="Ends" value={c.schedule.endAt ? new Date(c.schedule.endAt).toLocaleString() : "—"} />
                <Info label="Expires" value={c.schedule.expiresAt ? new Date(c.schedule.expiresAt).toLocaleString() : "—"} />
                <div className="rounded-md border bg-muted/40 p-3 text-xs text-muted-foreground">
                  Estimated delivery is calculated as reach × language variants.
                </div>
                <Info label="Estimated delivery" value={(c.estimatedReach * Math.max(1, c.languages.length)).toLocaleString()} />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="audience">
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Selected audience</CardTitle></CardHeader>
            <CardContent className="text-sm">
              {c.audienceGroupIds.length === 0 ? (
                <p className="text-muted-foreground">No audience groups selected.</p>
              ) : (
                <ul className="space-y-1">
                  {c.audienceGroupIds.map((g) => (
                    <li key={g} className="flex items-center justify-between rounded-md border bg-card px-3 py-2">
                      <span>{g}</span>
                      <span className="text-xs text-muted-foreground">Group</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="content">
          <Card className="shadow-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base">Communication preview</CardTitle>
              {tplQ.data && (
                <Link to="/templates/$id" params={{ id: tplQ.data.id }} className="text-xs text-primary hover:underline">
                  Open template
                </Link>
              )}
            </CardHeader>
            <CardContent>
              {tplQ.data ? (
                <div className="space-y-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {tplQ.data.name} · {tplQ.data.category} · {tplQ.data.language.toUpperCase()} · v{tplQ.data.version}
                  </p>
                  {tplQ.data.subject && <p className="font-semibold">{tplQ.data.subject}</p>}
                  <p className="whitespace-pre-line rounded-md border bg-muted/30 p-3 text-sm">{tplQ.data.body}</p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No template attached.</p>
              )}
              <div className="mt-4 rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
                Delivery summary and analytics will be available once the campaign has run.
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="qr">
          <PermissionGuard
            anyOf={[PERMISSIONS.CAMPAIGN_QR_VIEW]}
            fallback={<p className="text-sm text-muted-foreground">You don't have access to QR codes.</p>}
          >
            <CampaignQrPanel campaignId={id} campaignName={c.name} />
          </PermissionGuard>
        </TabsContent>

        <TabsContent value="translations">
          <PermissionGuard
            anyOf={[PERMISSIONS.TRANSLATION_USE, PERMISSIONS.CONTENT_EDIT]}
            fallback={<p className="text-sm text-muted-foreground">You don't have access to translations.</p>}
          >
            <MultilingualPanel parentType="campaign" parentId={id} />
          </PermissionGuard>
        </TabsContent>

        <TabsContent value="approvals">
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Approval workflow</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <ApprovalTimeline entries={c.approvals} />
              {c.status === "pending_approval" && (
                <PermissionGuard anyOf={[PERMISSIONS.APPROVAL_ACT]}>
                  <ApprovalActions
                    onApprove={async (comment) => { await approvalService.approve(id, actor, comment); toast.success("Approved"); invalidate(); }}
                    onReject={async (comment) => { await approvalService.reject(id, actor, comment); toast.success("Rejected"); invalidate(); }}
                    onSendBack={async (comment) => { await approvalService.sendBack(id, actor, comment); toast.success("Sent back for revision"); invalidate(); }}
                  />
                </PermissionGuard>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity">
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Activity & audit trail</CardTitle></CardHeader>
            <CardContent>
              <Timeline
                items={c.activity.map((e) => ({
                  id: e.id,
                  title: e.message,
                  description: e.actor,
                  at: e.at,
                  icon: Activity,
                }))}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notes">
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Internal notes</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Textarea
                  value={noteBody}
                  onChange={(e) => setNoteBody(e.target.value)}
                  placeholder="Add an internal note visible to your team…"
                  rows={3}
                />
                <div className="flex justify-end">
                  <Button
                    size="sm"
                    className="gap-1.5"
                    onClick={async () => {
                      if (!noteBody.trim()) return;
                      await campaignService.addNote(id, noteBody.trim(), actor.id, actor.name);
                      setNoteBody("");
                      invalidate();
                    }}
                  >
                    <MessageSquarePlus className="h-4 w-4" /> Add note
                  </Button>
                </div>
              </div>
              <ul className="space-y-2">
                {c.notes.length === 0 && <li className="text-sm text-muted-foreground">No notes yet.</li>}
                {c.notes.map((n) => (
                  <li key={n.id} className={cn("rounded-lg border bg-card p-3 text-sm", n.pinned && "border-primary/50 bg-primary/5")}>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">{n.authorName}</span>
                      <div className="flex items-center gap-2">
                        <span>{formatDistanceToNow(new Date(n.createdAt), { addSuffix: true })}</span>
                        <button
                          type="button"
                          onClick={async () => { await campaignService.togglePinNote(id, n.id); invalidate(); }}
                          className={cn("rounded p-1 text-muted-foreground hover:text-foreground", n.pinned && "text-primary")}
                          aria-label={n.pinned ? "Unpin note" : "Pin note"}
                        >
                          <Pin className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                    <p className="mt-1 whitespace-pre-line">{n.body}</p>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={!!confirm}
        onOpenChange={(o) => !o && setConfirm(null)}
        title={confirm?.title ?? ""}
        description={CAMPAIGN_STATUS_META[c.status].description}
        destructive={confirm?.destructive}
        confirmLabel="Confirm"
        onConfirm={async () => {
          await confirm?.action();
          setConfirm(null);
        }}
      />
    </div>
  );
}

function Info({ label, value, className }: { label: string; value: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex items-center justify-between rounded-md border bg-card px-3 py-2", className)}>
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground text-right">{value}</span>
    </div>
  );
}

function ApprovalActions({
  onApprove,
  onReject,
  onSendBack,
}: {
  onApprove: (comment?: string) => Promise<void>;
  onReject: (comment?: string) => Promise<void>;
  onSendBack: (comment?: string) => Promise<void>;
}) {
  const [comment, setComment] = useState("");
  return (
    <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
      <Textarea placeholder="Add a comment for the campaign owner…" value={comment} onChange={(e) => setComment(e.target.value)} rows={2} />
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => { onApprove(comment); setComment(""); }} className="gap-1.5">Approve</Button>
        <Button size="sm" variant="outline" onClick={() => { onSendBack(comment); setComment(""); }} className="gap-1.5">Send back</Button>
        <Button size="sm" variant="destructive" onClick={() => { onReject(comment); setComment(""); }} className="gap-1.5">Reject</Button>
      </div>
    </div>
  );
}
