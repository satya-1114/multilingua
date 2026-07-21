import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { formatDistanceToNow, format } from "date-fns";
import {
  BarChart3,
  Calendar,
  Megaphone,
  MessageSquare,
  Plus,
  Radio,
  Sparkles,
  Users,
} from "lucide-react";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatCard } from "@/components/common/stat-card";
import { SectionHeader } from "@/components/common/section-header";
import { StatusChip, statusChipToneFor } from "@/components/common/status-chip";
import { CardSkeleton, SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { EmptyState } from "@/components/common/empty-state";
import { PermissionGuard } from "@/components/common/permission-guard";
import { dashboardService } from "@/services/dashboard.service";
import { PERMISSIONS } from "@/constants/rbac";
import { useAuth } from "@/contexts/auth-context";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — Multilingua" },
      { name: "description", content: "Overview of your multilingual campaigns." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: DashboardPage,
});

const STAT_ICONS = [Megaphone, Radio, Users, BarChart3, MessageSquare, Sparkles];
const CHART_COLORS = ["#2563EB", "#0EA5E9", "#8B5CF6", "#22C55E", "#F59E0B", "#94A3B8"];

function DashboardPage() {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: () => dashboardService.getOverview(),
  });

  if (query.isLoading) {
    return (
      <div className="space-y-6">
        <SectionHeader title="Dashboard" description="Loading your workspace overview…" />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <SkeletonBlock rows={8} />
      </div>
    );
  }

  if (query.isError || !query.data) {
    return <ErrorState onRetry={() => query.refetch()} />;
  }

  const data = query.data;
  const firstName = user?.firstName ?? "there";

  return (
    <div className="space-y-6">
      <SectionHeader
        title={`Welcome back, ${firstName}`}
        description="Track campaigns, audiences, and delivery performance in real time."
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.CAMPAIGN_CREATE]}>
            <Button size="sm" className="gap-2">
              <Plus className="h-4 w-4" /> New campaign
            </Button>
          </PermissionGuard>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {data.stats.map((s, i) => (
          <StatCard
            key={s.key}
            label={s.label}
            value={s.value}
            delta={s.delta}
            trend={s.trend}
            helper={s.helper}
            icon={STAT_ICONS[i % STAT_ICONS.length]}
            index={i}
          />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="shadow-card xl:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-base">Delivery performance</CardTitle>
            <span className="text-xs text-muted-foreground">Last 7 days</span>
          </CardHeader>
          <CardContent className="pt-2">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={data.deliveryTrend}>
                <defs>
                  <linearGradient id="delivered" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="engaged" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#8B5CF6" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#8B5CF6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.2} />
                <XAxis dataKey="day" stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="delivered"
                  stroke="#2563EB"
                  strokeWidth={2}
                  fill="url(#delivered)"
                  name="Delivered"
                />
                <Area
                  type="monotone"
                  dataKey="engaged"
                  stroke="#8B5CF6"
                  strokeWidth={2}
                  fill="url(#engaged)"
                  name="Engaged"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">Language distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={230}>
              <PieChart>
                <Pie
                  data={data.languageDistribution}
                  dataKey="value"
                  nameKey="language"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                >
                  {data.languageDistribution.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend
                  iconType="circle"
                  wrapperStyle={{ fontSize: 11 }}
                  formatter={(v) => <span className="text-muted-foreground">{v}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="shadow-card xl:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">Upcoming campaigns</CardTitle>
            <Button variant="ghost" size="sm" className="gap-1 text-xs">
              <Calendar className="h-3.5 w-3.5" /> View calendar
            </Button>
          </CardHeader>
          <CardContent>
            {data.upcoming.length === 0 ? (
              <EmptyState title="No scheduled campaigns" description="Plan a new campaign to see it here." />
            ) : (
              <ul className="divide-y divide-border">
                {data.upcoming.map((c) => (
                  <li key={c.id} className="flex items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">{c.name}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {c.channel} · {c.languages} languages · {c.audience.toLocaleString()} contacts
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <StatusChip label={c.status} tone={statusChipToneFor(c.status)} />
                      <span className="text-[11px] text-muted-foreground">
                        {format(new Date(c.scheduledFor), "MMM d, HH:mm")}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">Campaign status</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={data.campaignStatus}>
                <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
                <XAxis dataKey="status" stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} fill="#2563EB" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle className="text-base">Audience growth</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={data.audienceGrowth}>
              <defs>
                <linearGradient id="audience" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0EA5E9" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#0EA5E9" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" strokeOpacity={0.15} />
              <XAxis dataKey="month" stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="currentColor" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Area
                type="monotone"
                dataKey="audience"
                stroke="#0EA5E9"
                strokeWidth={2}
                fill="url(#audience)"
                name="Audience"
              />
              <Area
                type="monotone"
                dataKey="engaged"
                stroke="#22C55E"
                strokeWidth={2}
                fill="transparent"
                name="Engaged"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="shadow-card xl:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Recent activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {data.activity.map((a, i) => (
                <motion.li
                  key={a.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-start gap-3"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                    {a.actorInitials}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-foreground">
                      <span className="font-semibold">{a.actorName}</span>{" "}
                      <span className="text-muted-foreground">{a.action}</span>{" "}
                      <span className="font-medium">{a.target}</span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(a.timestamp), { addSuffix: true })}
                    </p>
                  </div>
                </motion.li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="text-base">Quick actions</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2">
              <PermissionGuard anyOf={[PERMISSIONS.CAMPAIGN_CREATE]}>
                <Button variant="outline" className="h-auto justify-start gap-2 py-3">
                  <Megaphone className="h-4 w-4" /> New campaign
                </Button>
              </PermissionGuard>
              <PermissionGuard anyOf={[PERMISSIONS.CONTENT_CREATE]}>
                <Button variant="outline" className="h-auto justify-start gap-2 py-3">
                  <Sparkles className="h-4 w-4" /> AI compose
                </Button>
              </PermissionGuard>
              <PermissionGuard anyOf={[PERMISSIONS.AUDIENCE_MANAGE]}>
                <Button variant="outline" className="h-auto justify-start gap-2 py-3">
                  <Users className="h-4 w-4" /> Import audience
                </Button>
              </PermissionGuard>
              <Button variant="outline" className="h-auto justify-start gap-2 py-3">
                <BarChart3 className="h-4 w-4" /> View reports
              </Button>
            </CardContent>
          </Card>

          <Card className="shadow-card">
            <CardHeader>
              <CardTitle className="text-base">Announcements</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.announcements.map((a) => (
                <div key={a.id} className="rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-foreground">{a.title}</p>
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                      {a.tag}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{a.body}</p>
                  <p className="mt-2 text-[11px] text-muted-foreground">
                    {formatDistanceToNow(new Date(a.publishedAt), { addSuffix: true })}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
