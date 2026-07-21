import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { OrganizationForm } from "@/components/common/organization-form";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { EmptyState } from "@/components/common/empty-state";
import { Button } from "@/components/ui/button";
import { organizationService } from "@/services/organization.service";

export const Route = createFileRoute("/_authenticated/organizations/$id/edit")({
  head: () => ({ meta: [{ title: "Edit organization — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: EditOrganizationPage,
});

function EditOrganizationPage() {
  const { id } = Route.useParams();
  const query = useQuery({ queryKey: ["organizations", id], queryFn: () => organizationService.get(id) });

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="gap-2 text-muted-foreground">
        <Link to="/organizations/$id" params={{ id }}><ArrowLeft className="h-4 w-4" /> Back</Link>
      </Button>
      <SectionHeader title="Edit organization" description="Update details, contact information, and localization." />
      {query.isLoading ? <SkeletonBlock rows={10} /> : query.data ? (
        <OrganizationForm mode="edit" initial={query.data} />
      ) : (
        <EmptyState title="Organization not found" />
      )}
    </div>
  );
}
