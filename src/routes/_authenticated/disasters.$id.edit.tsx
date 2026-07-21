import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { DisasterForm } from "@/components/common/disaster-form";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { RoleGuard } from "@/components/common/role-guard";
import { ROLES } from "@/constants/rbac";
import { disasterService } from "@/services/disaster.service";

export const Route = createFileRoute("/_authenticated/disasters/$id/edit")({
  head: () => ({
    meta: [
      { title: "Edit disaster — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: EditDisasterPage,
});

function EditDisasterPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["disaster", id], queryFn: () => disasterService.get(id) });

  return (
    <RoleGuard allow={[ROLES.SUPER_ADMIN, ROLES.CAMPAIGN_MANAGER]} mode="redirect">
      <div className="space-y-6">
        <SectionHeader title="Edit disaster" description="Update disaster details, safety instructions and public visibility." />
        {q.isLoading ? (
          <SkeletonBlock rows={10} />
        ) : q.isError || !q.data ? (
          <ErrorState title="Disaster not found" onRetry={() => q.refetch()} />
        ) : (
          <DisasterForm
            initial={q.data}
            submitLabel="Save changes"
            onCancel={() => navigate({ to: "/disasters/$id", params: { id } })}
            onSubmit={async (input) => {
              try {
                await disasterService.update(id, input);
                qc.invalidateQueries({ queryKey: ["disaster", id] });
                qc.invalidateQueries({ queryKey: ["disasters"] });
                toast.success("Disaster updated");
                navigate({ to: "/disasters/$id", params: { id } });
              } catch (e) {
                toast.error((e as Error).message || "Could not save changes");
              }
            }}
          />
        )}
      </div>
    </RoleGuard>
  );
}
