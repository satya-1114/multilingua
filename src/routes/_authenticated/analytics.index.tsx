import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, Sparkles, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { analyticsService } from "@/services/analytics.service";

export const Route = createFileRoute("/_authenticated/analytics/")({
  component: AnalyticsOverviewPage,
});

const COLORS = ["#2563EB", "#0EA5E9", "#8B5CF6", "#22C55E", "#F59E0B", "#DC2626"];

function AnalyticsOverviewPage() {
  const q = useQuery({ queryKey: ["analytics", "overview"], queryFn: () => analyticsService.overview() });
  const d = q.data;
  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-4">
        {(d?.kpis ?? []).map((k, i) => (
          <AnalyticsCard
            key={k.label}
            label={k.label}
            value={k.value}
            delta={k.delta}
            helper={k.helper}
            icon={[BarChart3, Users, Sparkles, BarChart3][i % 4]}
          />
        ))}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Communication reach (30d)">
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={d?.reach ?? []}>
              <defs>
                <linearGradient id="reach" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#2563EB" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area dataKey="delivered" stroke="#2563EB" fill="url(#reach)" />
              <Area dataKey="engaged" stroke="#8B5CF6" fill="transparent" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Audience growth">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={d?.audienceGrowth ?? []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line dataKey="total" stroke="#0EA5E9" strokeWidth={2} dot={false} />
              <Line dataKey="verified" stroke="#22C55E" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Language distribution">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={d?.languages ?? []} dataKey="value" nameKey="label" outerRadius={80}>
                {(d?.languages ?? []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Organization comparison">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d?.organizations ?? []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#2563EB" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Engagement trends">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={d?.engagement ?? []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line dataKey="open" stroke="#2563EB" dot={false} />
              <Line dataKey="click" stroke="#8B5CF6" dot={false} />
              <Line dataKey="reply" stroke="#22C55E" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Delivery by channel">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d?.delivery ?? []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="sms" stackId="a" fill="#2563EB" />
              <Bar dataKey="email" stackId="a" fill="#0EA5E9" />
              <Bar dataKey="whatsapp" stackId="a" fill="#22C55E" />
              <Bar dataKey="push" stackId="a" fill="#F59E0B" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        {(d?.approvals ?? []).map((k) => (
          <AnalyticsCard key={k.label} label={k.label} value={k.value} helper={k.helper} />
        ))}
      </div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="shadow-card">
      <CardHeader className="pb-2"><CardTitle className="text-sm">{title}</CardTitle></CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
