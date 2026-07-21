import { createFileRoute, Link, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StatCard } from "@/components/common/stat-card";
import { DeliveryStatusBadge } from "@/components/common/delivery-status-badge";
import { DeliveryProgressIndicator } from "@/components/common/delivery-progress-indicator";
import { RecipientCard } from "@/components/common/recipient-card";
import { CommunicationActivityFeed } from "@/components/common/communication-activity-feed";
import { DeliveryTimeline } from "@/components/common/delivery-timeline";
import { EngagementChart } from "@/components/common/engagement-chart";
import { deliveryService } from "@/services/delivery.service";
import { communicationService } from "@/services/communication.service";

export const Route = createFileRoute("/_authenticated/campaigns/$id/delivery")({
  head: () => ({ meta: [{ title: "Campaign delivery" }, { name: "robots", content: "noindex" }] }),
  component: CampaignDeliveryPage,
});

function CampaignDeliveryPage() {
  const { id } = Route.useParams();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  void pathname;
  const [tab, setTab] = useState("delivery");
  const jobs = useQuery({ queryKey: ["campaign-jobs", id], queryFn: () => deliveryService.list({ campaignId: id }) });
  const recipients = useQuery({ queryKey: ["campaign-recipients", id], queryFn: () => deliveryService.recipients(id) });
  const timeline = useQuery({ queryKey: ["campaign-timeline", id], queryFn: () => communicationService.timeline(id) });

  const items = jobs.data?.items ?? [];
  const totals = items.reduce(
    (a, j) => ({
      total: a.total + j.totalRecipients,
      delivered: a.delivered + j.delivered,
      failed: a.failed + j.failed,
      opened: a.opened + j.opened,
      clicked: a.clicked + j.clicked,
      responded: a.responded + j.responded,
    }),
    { total: 0, delivered: 0, failed: 0, opened: 0, clicked: 0, responded: 0 },
  );

  const rec = recipients.data ?? [];
  const failed = rec.filter((r) => r.status === "failed" || r.status === "bounced");
  const responded = rec.filter((r) => r.status === "responded");

  return (
    <div className="space-y-4">
        <Button asChild variant="ghost" size="sm">
          <Link to="/campaigns/$id" params={{ id }}><ArrowLeft className="mr-2 h-4 w-4" />Back to campaign</Link>
        </Button>

        <div>
          <h2 className="text-xl font-semibold">Campaign delivery</h2>
          <p className="text-sm text-muted-foreground">Detailed delivery, recipient, and engagement view for this campaign.</p>
        </div>

        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Total" value={totals.total.toLocaleString()} />
          <StatCard label="Delivered" value={totals.delivered.toLocaleString()} />
          <StatCard label="Failed" value={totals.failed.toLocaleString()} />
          <StatCard label="Opened" value={totals.opened.toLocaleString()} />
          <StatCard label="Clicked" value={totals.clicked.toLocaleString()} />
          <StatCard label="Responded" value={totals.responded.toLocaleString()} />
        </div>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="delivery">Delivery</TabsTrigger>
            <TabsTrigger value="recipients">Recipients</TabsTrigger>
            <TabsTrigger value="failures">Failures</TabsTrigger>
            <TabsTrigger value="responses">Responses</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
          </TabsList>

          <TabsContent value="delivery" className="space-y-3">
            {items.length === 0 && <p className="text-sm text-muted-foreground">No delivery jobs.</p>}
            {items.map((j) => (
              <Card key={j.id}>
                <CardContent className="p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <DeliveryStatusBadge status={j.status} />
                    <span className="text-sm font-medium">{j.campaignName}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{j.totalRecipients.toLocaleString()} recipients</span>
                  </div>
                  <DeliveryProgressIndicator job={j} />
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          <TabsContent value="recipients">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {rec.map((r) => <RecipientCard key={r.id} recipient={r} />)}
            </div>
          </TabsContent>

          <TabsContent value="failures" className="space-y-3">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Failed & bounced recipients</CardTitle></CardHeader>
              <CardContent>
                {failed.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No failures recorded.</p>
                ) : (
                  <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {failed.map((r) => <RecipientCard key={r.id} recipient={r} />)}
                  </div>
                )}
              </CardContent>
            </Card>
            <CommunicationActivityFeed jobs={items.filter((j) => j.status === "failed")} title="Failed delivery jobs" />
          </TabsContent>

          <TabsContent value="responses">
            {responded.length === 0 ? (
              <p className="text-sm text-muted-foreground">No responses yet.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {responded.map((r) => <RecipientCard key={r.id} recipient={r} />)}
              </div>
            )}
          </TabsContent>

          <TabsContent value="analytics">
            <EngagementChart
              title="Recipient outcomes"
              type="bar"
              xKey="label"
              data={[
                { label: "Delivered", value: totals.delivered },
                { label: "Opened", value: totals.opened },
                { label: "Clicked", value: totals.clicked },
                { label: "Responded", value: totals.responded },
                { label: "Failed", value: totals.failed },
              ]}
              series={[{ key: "value", label: "Count", color: "#2563EB" }]}
            />
          </TabsContent>

          <TabsContent value="timeline">
            <Card><CardContent className="p-4"><DeliveryTimeline events={timeline.data ?? []} /></CardContent></Card>
          </TabsContent>
        </Tabs>
      </div>
  );
}
