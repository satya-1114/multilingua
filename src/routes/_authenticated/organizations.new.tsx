import { createFileRoute } from "@tanstack/react-router";
import { SectionHeader } from "@/components/common/section-header";
import { OrganizationForm } from "@/components/common/organization-form";

export const Route = createFileRoute("/_authenticated/organizations/new")({
  head: () => ({ meta: [{ title: "New organization — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: NewOrganizationPage,
});

function NewOrganizationPage() {
  return (
    <div className="space-y-6">
      <SectionHeader title="New organization" description="Create a new tenant organization on the platform." />
      <OrganizationForm mode="create" />
    </div>
  );
}
