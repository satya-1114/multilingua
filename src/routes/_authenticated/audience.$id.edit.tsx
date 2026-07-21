import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { AudienceForm } from "@/components/common/audience-form";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { EmptyState } from "@/components/common/empty-state";
import { Button } from "@/components/ui/button";
import { audienceService } from "@/services/audience.service";

export const Route = createFileRoute("/_authenticated/audience/$id/edit")({
  head: () => ({ meta: [{ title: "Edit contact — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: EditAudiencePage,
});

function EditAudiencePage() {
  const { id } = Route.useParams();
  const contactQuery = useQuery({ queryKey: ["audience", id], queryFn: () => audienceService.get(id) });

  return (
    <div className="space-y-6">
      <Button variant="ghost" size="sm" asChild className="gap-2 text-muted-foreground">
        <Link to="/audience/$id" params={{ id }}><ArrowLeft className="h-4 w-4" /> Back to contact</Link>
      </Button>
      <SectionHeader title="Edit contact" description="Update contact information and preferences." />
      {contactQuery.isLoading ? (
        <SkeletonBlock rows={12} />
      ) : contactQuery.data ? (
        <AudienceForm mode="edit" initial={contactQuery.data} />
      ) : (
        <EmptyState title="Contact not found" />
      )}
    </div>
  );
}
