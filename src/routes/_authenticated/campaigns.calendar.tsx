import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { SectionHeader } from "@/components/common/section-header";
import { CampaignCalendar } from "@/components/common/campaign-calendar";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { campaignService } from "@/services/campaign.service";
import { CAMPAIGN_STATUSES } from "@/constants/campaign";
import type { CampaignStatus } from "@/types/campaign";
import { CampaignStatusBadge } from "@/components/common/campaign-status-badge";
import { Link } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/campaigns/calendar")({
  head: () => ({
    meta: [
      { title: "Campaign calendar — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: CampaignCalendarPage,
});

function CampaignCalendarPage() {
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | "all">("all");
  const listQ = useQuery({
    queryKey: ["campaigns", "calendar"],
    queryFn: () => campaignService.listAll({ pageSize: 200 }),
  });

  const filtered = useMemo(() => {
    if (!listQ.data) return [];
    if (statusFilter === "all") return listQ.data;
    return listQ.data.filter((c) => c.status === statusFilter);
  }, [listQ.data, statusFilter]);

  const upcoming = useMemo(() => {
    const now = Date.now();
    return (listQ.data ?? [])
      .filter((c) => c.schedule.startAt && new Date(c.schedule.startAt).getTime() > now)
      .sort((a, b) => (a.schedule.startAt! < b.schedule.startAt! ? -1 : 1))
      .slice(0, 8);
  }, [listQ.data]);

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Campaign calendar"
        description="Monthly view of scheduled and running campaigns across the workspace."
        actions={
          <div className="flex items-center gap-2">
            <Label className="text-xs uppercase tracking-wide text-muted-foreground">Status</Label>
            <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as CampaignStatus | "all")}>
              <SelectTrigger className="h-8 w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {CAMPAIGN_STATUSES.map((s) => (
                  <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        }
      />

      {listQ.isLoading ? (
        <SkeletonBlock rows={12} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1fr,320px]">
          <CampaignCalendar campaigns={filtered} />
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Upcoming</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                {upcoming.length === 0 && <li className="text-muted-foreground">Nothing scheduled ahead.</li>}
                {upcoming.map((c) => (
                  <li key={c.id} className="rounded-lg border bg-card p-3">
                    <div className="flex items-center justify-between gap-2">
                      <Link to="/campaigns/$id" params={{ id: c.id }} className="min-w-0 truncate font-medium hover:text-primary">
                        {c.name}
                      </Link>
                      <CampaignStatusBadge status={c.status} showDot={false} />
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(c.schedule.startAt!).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
