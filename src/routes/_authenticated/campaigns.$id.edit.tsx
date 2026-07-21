import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { CampaignWizard } from "@/components/common/campaign-wizard";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { campaignService } from "@/services/campaign.service";

export const Route = createFileRoute("/_authenticated/campaigns/$id/edit")({
  head: () => ({
    meta: [
      { title: "Edit campaign — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: EditCampaignPage,
});

function EditCampaignPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const cq = useQuery({ queryKey: ["campaign", id], queryFn: () => campaignService.get(id) });

  if (cq.isLoading) return <SkeletonBlock rows={8} />;
  if (cq.isError || !cq.data) return <ErrorState onRetry={() => cq.refetch()} />;
  const c = cq.data;

  return (
    <div className="space-y-6">
      <SectionHeader title={`Edit — ${c.name}`} description={c.code} />
      <CampaignWizard
        initial={{
          name: c.name,
          description: c.description,
          objective: c.objective,
          type: c.type,
          category: c.category,
          priority: c.priority,
          visibility: c.visibility,
          color: c.color,
          tags: c.tags,
          organizationId: c.organizationId,
          department: c.department,
          ownerId: c.ownerId,
          audienceGroupIds: c.audienceGroupIds,
          audienceContactIds: c.audienceContactIds,
          languages: c.languages,
          templateId: c.templateId,
          schedule: c.schedule,
        }}
        submitLabel="Save changes"
        onCancel={() => navigate({ to: "/campaigns/$id", params: { id } })}
        onSubmit={async (input) => {
          await campaignService.update(id, input);
          qc.invalidateQueries({ queryKey: ["campaign", id] });
          qc.invalidateQueries({ queryKey: ["campaigns"] });
          toast.success("Campaign updated");
          navigate({ to: "/campaigns/$id", params: { id } });
        }}
      />
    </div>
  );
}
