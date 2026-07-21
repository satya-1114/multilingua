import { createFileRoute } from "@tanstack/react-router";
import { SectionHeader } from "@/components/common/section-header";
import { AudienceForm } from "@/components/common/audience-form";

export const Route = createFileRoute("/_authenticated/audience/new")({
  head: () => ({ meta: [{ title: "New contact — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: NewAudiencePage,
});

function NewAudiencePage() {
  return (
    <div className="space-y-6">
      <SectionHeader title="New contact" description="Add a new audience contact to your organization." />
      <AudienceForm mode="create" />
    </div>
  );
}
