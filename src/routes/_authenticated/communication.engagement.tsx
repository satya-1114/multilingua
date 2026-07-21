import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { MailOpen, MousePointerClick, MessageSquare, Share2, Download, UserPlus, Users, Activity, Smile } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/common/stat-card";
import { EngagementChart } from "@/components/common/engagement-chart";
import { engagementService } from "@/services/engagement.service";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/communication/engagement")({
  component: EngagementPage,
});

const dayOrder = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function EngagementPage() {
  const q = useQuery({ queryKey: ["engagement", "overview"], queryFn: () => engagementService.overview() });
  const d = q.data;
  const m = d?.metrics;
  const fmt = (n?: number) => (n ?? 0).toLocaleString();

  const heatMax = Math.max(1, ...(d?.heatmap ?? []).map((c) => c.value));

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
        <StatCard label="Opens" value={fmt(m?.opens)} icon={MailOpen} />
        <StatCard label="Clicks" value={fmt(m?.clicks)} icon={MousePointerClick} />
        <StatCard label="Replies" value={fmt(m?.replies)} icon={MessageSquare} />
        <StatCard label="Shares" value={fmt(m?.shares)} icon={Share2} />
        <StatCard label="Downloads" value={fmt(m?.downloads)} icon={Download} />
        <StatCard label="Registrations" value={fmt(m?.registrations)} icon={UserPlus} />
        <StatCard label="Attendance" value={fmt(m?.attendance)} icon={Users} />
        <StatCard label="Participation" value={`${m?.participation ?? 0}%`} icon={Activity} />
        <StatCard label="Sentiment" value={`${m?.sentimentScore ?? 0}`} icon={Smile} helper="0–100" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <EngagementChart
          title="Engagement trend (14d)"
          data={(d?.trends ?? []).map((p) => ({ ...p }))}
          xKey="date"
          series={[
            { key: "opens", label: "Opens", color: "#2563EB" },
            { key: "clicks", label: "Clicks", color: "#8B5CF6" },
            { key: "replies", label: "Replies", color: "#22C55E" },
          ]}
        />
        <EngagementChart title="Channel comparison" type="bar"
          data={(d?.channelComparison ?? []).map((p) => ({ ...p }))}
          xKey="label"
          series={[
            { key: "opens", label: "Opens", color: "#2563EB" },
            { key: "clicks", label: "Clicks", color: "#8B5CF6" },
            { key: "replies", label: "Replies", color: "#22C55E" },
          ]}
        />
        <EngagementChart title="Language comparison" type="bar"
          data={(d?.languageComparison ?? []).map((p) => ({ ...p }))}
          xKey="label"
          series={[
            { key: "opens", label: "Opens", color: "#0EA5E9" },
            { key: "clicks", label: "Clicks", color: "#F59E0B" },
            { key: "replies", label: "Replies", color: "#DC2626" },
          ]}
        />
        <EngagementChart title="Audience comparison" type="bar"
          data={(d?.audienceComparison ?? []).map((p) => ({ ...p }))}
          xKey="label"
          series={[
            { key: "opens", label: "Opens", color: "#2563EB" },
            { key: "clicks", label: "Clicks", color: "#8B5CF6" },
            { key: "replies", label: "Replies", color: "#22C55E" },
          ]}
        />
      </div>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Engagement heatmap (day × hour)</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto">
          <div className="min-w-[720px]">
            <div className="mb-1 grid grid-cols-[80px_repeat(24,minmax(0,1fr))] gap-1 text-[10px] text-muted-foreground">
              <div />
              {Array.from({ length: 24 }, (_, h) => <div key={h} className="text-center">{h}</div>)}
            </div>
            {dayOrder.map((day) => (
              <div key={day} className="grid grid-cols-[80px_repeat(24,minmax(0,1fr))] items-center gap-1">
                <div className="text-xs font-medium">{day}</div>
                {Array.from({ length: 24 }, (_, h) => {
                  const cell = (d?.heatmap ?? []).find((c) => c.day === day && c.hour === h);
                  const intensity = cell ? cell.value / heatMax : 0;
                  return (
                    <div key={h} className={cn("h-5 rounded-sm")}
                      style={{ background: `rgba(37, 99, 235, ${0.08 + intensity * 0.75})` }}
                      title={`${day} ${h}:00 · ${cell?.value ?? 0}`} />
                  );
                })}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
