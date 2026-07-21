import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import { SectionHeader } from "@/components/common/section-header";
import { EmptyState } from "@/components/common/empty-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { approvalService } from "@/services/approval.service";
import { PERMISSIONS } from "@/constants/rbac";
import { useAuth } from "@/contexts/auth-context";

export const Route = createFileRoute("/_authenticated/campaigns/approvals")({
  head: () => ({
    meta: [
      { title: "Campaign approvals — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ApprovalsPage,
});

function ApprovalsPage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["approvals", "pending"], queryFn: () => approvalService.pendingQueue() });

  const actor = { id: user?.id ?? "user-1", name: user?.fullName ?? "You" };

  async function act(id: string, kind: "approve" | "reject" | "sendBack") {
    if (kind === "approve") await approvalService.approve(id, actor);
    if (kind === "reject") await approvalService.reject(id, actor);
    if (kind === "sendBack") await approvalService.sendBack(id, actor);
    toast.success(kind === "approve" ? "Approved" : kind === "reject" ? "Rejected" : "Sent back");
    qc.invalidateQueries({ queryKey: ["approvals"] });
    qc.invalidateQueries({ queryKey: ["campaigns"] });
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Approval queue"
        description="Review, approve, or send back campaigns awaiting your decision."
      />
      <Card className="shadow-card">
        <CardHeader className="pb-2"><CardTitle className="text-base">Pending approvals</CardTitle></CardHeader>
        <CardContent>
          {q.isLoading ? (
            <SkeletonBlock rows={5} />
          ) : (q.data ?? []).length === 0 ? (
            <EmptyState title="Nothing pending" description="You're all caught up." />
          ) : (
            <ul className="divide-y">
              {q.data!.map((c) => (
                <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <Link to="/campaigns/$id" params={{ id: c.id }} className="block truncate font-medium text-foreground hover:text-primary">
                      {c.name}
                    </Link>
                    <p className="text-xs text-muted-foreground">
                      {c.code} · Submitted {formatDistanceToNow(new Date(c.updatedAt), { addSuffix: true })} by {c.ownerName}
                    </p>
                  </div>
                  <PermissionGuard anyOf={[PERMISSIONS.APPROVAL_ACT]}>
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" onClick={() => act(c.id, "approve")}>Approve</Button>
                      <Button size="sm" variant="outline" onClick={() => act(c.id, "sendBack")}>Send back</Button>
                      <Button size="sm" variant="destructive" onClick={() => act(c.id, "reject")}>Reject</Button>
                    </div>
                  </PermissionGuard>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
