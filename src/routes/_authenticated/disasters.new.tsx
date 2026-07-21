import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { DisasterForm } from "@/components/common/disaster-form";
import { RoleGuard } from "@/components/common/role-guard";
import { ROLES } from "@/constants/rbac";
import { disasterService } from "@/services/disaster.service";

export const Route = createFileRoute("/_authenticated/disasters/new")({
  head: () => ({
    meta: [
      { title: "New disaster — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: NewDisasterPage,
});

function NewDisasterPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  return (
    <RoleGuard allow={[ROLES.SUPER_ADMIN, ROLES.CAMPAIGN_MANAGER]} mode="redirect">
      <div className="space-y-6">
        <SectionHeader
          title="New disaster"
          description="Declare a disaster to open the coordination view for campaigns, volunteers and public alerts."
        />
        <DisasterForm
          onCancel={() => navigate({ to: "/disasters" })}
          onSubmit={async (input) => {
            try {
              const created = await disasterService.create(input);
              qc.invalidateQueries({ queryKey: ["disasters"] });
              toast.success("Disaster created");
              navigate({ to: "/disasters/$id", params: { id: created.id } });
            } catch (e) {
              toast.error((e as Error).message || "Could not create disaster");
            }
          }}
        />
      </div>
    </RoleGuard>
  );
}
