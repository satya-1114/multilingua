import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionHeader } from "@/components/common/section-header";
import { IntegrationCard } from "@/components/common/integration-card";
import { integrationService } from "@/services/integration.service";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { IntegrationCategory, Integration } from "@/types/integration";
import { Button } from "@/components/ui/button";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/integrations/")({
  head: () => ({ meta: [{ title: "Integrations" }, { name: "robots", content: "noindex" }] }),
  component: IntegrationsPage,
});

const categories: { value: IntegrationCategory | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "email", label: "Email" },
  { value: "sms", label: "SMS" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "push", label: "Push" },
  { value: "social", label: "Social" },
  { value: "api", label: "APIs" },
];

function IntegrationsPage() {
  const qc = useQueryClient();
  const [cat, setCat] = useState<IntegrationCategory | "all">("all");
  const list = useQuery({ queryKey: ["integrations"], queryFn: () => integrationService.list() });
  const filtered = useMemo(() => (list.data ?? []).filter((i) => cat === "all" || i.category === cat), [list.data, cat]);

  async function toggle(i: Integration) {
    await integrationService.setStatus(i.id, i.status === "connected" ? "disconnected" : "connected");
    qc.invalidateQueries({ queryKey: ["integrations"] });
  }

  return (
    <div className="space-y-5">
        <SectionHeader
          title="Integration center"
          description="Connect communication providers, APIs, and webhooks."
          actions={
            <Button asChild variant="outline">
              <Link to="/integrations/webhooks">Webhook manager</Link>
            </Button>
          }
        />
        <Tabs value={cat} onValueChange={(v) => setCat(v as typeof cat)}>
          <TabsList className="flex-wrap">
            {categories.map((c) => <TabsTrigger key={c.value} value={c.value}>{c.label}</TabsTrigger>)}
          </TabsList>
        </Tabs>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((i) => <IntegrationCard key={i.id} integration={i} onToggle={toggle} />)}
        </div>
      </div>
  );
}
