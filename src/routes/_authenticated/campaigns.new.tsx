import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { CampaignWizard } from "@/components/common/campaign-wizard";
import { campaignService } from "@/services/campaign.service";
import { useAuth } from "@/contexts/auth-context";

export const Route = createFileRoute("/_authenticated/campaigns/new")({
  head: () => ({
    meta: [
      { title: "New campaign — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: NewCampaignPage,
});

function NewCampaignPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const qc = useQueryClient();

  return (
    <div className="space-y-6">
      <SectionHeader
        title="New campaign"
        description="Set up basics, choose an audience, pick a template, and schedule delivery."
      />
      <CampaignWizard
        initial={{ ownerId: user?.id ?? "user-1" }}
        submitLabel="Create campaign"
        onCancel={() => navigate({ to: "/campaigns" })}
        onSubmit={async (input) => {
          const created = await campaignService.create(input, user?.fullName ?? "You");
          qc.invalidateQueries({ queryKey: ["campaigns"] });
          toast.success("Campaign created");
          navigate({ to: "/campaigns/$id", params: { id: created.id } });
        }}
      />
    </div>
  );
}
