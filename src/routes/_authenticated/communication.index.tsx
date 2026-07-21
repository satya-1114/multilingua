import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Send, CheckCircle2, XCircle, Clock, CalendarClock, MailOpen, MousePointerClick, MessageSquare, AlertTriangle, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/common/stat-card";
import { CommunicationActivityFeed } from "@/components/common/communication-activity-feed";
import { communicationService } from "@/services/communication.service";

export const Route = createFileRoute("/_authenticated/communication/")({
  component: CommunicationOverviewPage,
});

const COLORS = ["#2563EB", "#0EA5E9", "#8B5CF6", "#22C55E", "#F59E0B", "#DC2626"];

function CommunicationOverviewPage() {
  const q = useQuery({ queryKey: ["communication", "overview"], queryFn: () => communicationService.overview() });
  const d = q.data;
  const k = d?.kpis;
  const fmt = (n?: number) => (n ?? 0).toLocaleString();
  const pct = (n?: number) => `${(n ?? 0).toFixed(1)}%`;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
        <StatCard label="Messages sent" value={fmt(k?.sent)} icon={Send} />
        <StatCard label="Delivered" value={fmt(k?.delivered)} icon={CheckCircle2} trend="up" delta="+3.2%" />
        <StatCard label="Failed" value={fmt(k?.failed)} icon={XCircle} trend="down" delta="-0.4%" />
        <StatCard label="Queued" value={fmt(k?.queued)} icon={Clock} />
        <StatCard label="Scheduled" value={fmt(k?.scheduled)} icon={CalendarClock} />
      </div>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
        <StatCard label="Open rate" value={pct(k?.openRate)} icon={MailOpen} trend="up" delta="+1.1%" />
        <StatCard label="Click rate" value={pct(k?.clickRate)} icon={MousePointerClick} trend="up" delta="+0.6%" />
        <StatCard label="Response rate" value={pct(k?.responseRate)} icon={MessageSquare} />
        <StatCard label="Bounce rate" value={pct(k?.bounceRate)} icon={AlertTriangle} trend="down" delta="-0.2%" />
        <StatCard label="Delivery success" value={pct(k?.deliverySuccessRate)} icon={TrendingUp} trend="up" delta="+0.3%" />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Chart title="Delivery timeline (14d)">
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={d?.deliveryTimeline ?? []}>
              <defs>
                <linearGradient id="dt" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#2563EB" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area name="Sent" dataKey="value" stroke="#2563EB" fill="url(#dt)" />
              <Area name="Delivered" dataKey="secondary" stroke="#22C55E" fill="transparent" />
            </AreaChart>
          </ResponsiveContainer>
        </Chart>
        <Chart title="Channel distribution">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={d?.channelDistribution ?? []} dataKey="value" nameKey="label" outerRadius={90}>
                {(d?.channelDistribution ?? []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Legend /><Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Chart>
        <Chart title="Language distribution">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={d?.languageDistribution ?? []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#8B5CF6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Chart>
        <Chart title="Daily delivery trend (30d)">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={d?.dailyTrend ?? []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line dataKey="value" stroke="#0EA5E9" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Chart>
        <Chart title="Audience engagement (open % / reply %)">
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={d?.engagement ?? []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip /><Legend />
              <Line name="Open %" dataKey="value" stroke="#2563EB" strokeWidth={2} dot={false} />
              <Line name="Reply %" dataKey="secondary" stroke="#22C55E" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Chart>
        <Chart title="Failure analysis">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={d?.failureBreakdown ?? []} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={130} />
              <Tooltip />
              <Bar dataKey="count" fill="#DC2626" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Chart>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <CommunicationActivityFeed jobs={d?.recentDeliveries ?? []} title="Recent deliveries" />
        <CommunicationActivityFeed jobs={d?.recentFailures ?? []} title="Recent failures" />
        <CommunicationActivityFeed jobs={d?.upcomingScheduled ?? []} title="Upcoming scheduled" />
      </div>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">Quick actions</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button asChild size="sm"><Link to="/campaigns/new">New campaign</Link></Button>
          <Button asChild size="sm" variant="outline"><Link to="/communication/delivery">Open delivery queues</Link></Button>
          <Button asChild size="sm" variant="outline"><Link to="/communication/scheduling">Schedule broadcast</Link></Button>
          <Button asChild size="sm" variant="outline"><Link to="/communication/channels">Manage channels</Link></Button>
          <Button asChild size="sm" variant="outline"><Link to="/notifications/preferences">Notification preferences</Link></Button>
        </CardContent>
      </Card>
    </div>
  );
}

function Chart({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle></CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
