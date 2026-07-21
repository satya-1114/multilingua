import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { queryKeys } from "@/lib/queryKeys";
import { analyticsService } from "@/services/analytics.service";

export const Route = createFileRoute("/_authenticated/analytics/snapshots/$id")({
  head: () => ({
    meta: [
      { title: "Snapshot detail — Analytics" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: SnapshotDetailPage,
});

function SnapshotDetailPage() {
  const { id } = Route.useParams();
  const q = useQuery({
    queryKey: queryKeys.analyticsSnapshots.detail(id),
    queryFn: () => analyticsService.getSnapshot(id),
  });

  if (q.isLoading) return <Skeleton className="h-64 w-full" />;
  if (q.isError)
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load snapshot</AlertTitle>
        <AlertDescription>{(q.error as Error).message}</AlertDescription>
      </Alert>
    );
  const s = q.data!;

  const chartData = Object.entries(s.metricsJson ?? {})
    .filter(([, v]) => typeof v === "number")
    .map(([k, v]) => ({ name: k, value: v as number }));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/analytics/snapshots">
            <ArrowLeft className="mr-1 h-4 w-4" /> Back
          </Link>
        </Button>
      </div>

      <Card className="shadow-card">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{s.snapshotType}</Badge>
            <CardTitle className="text-base">
              {new Date(s.periodStart).toLocaleDateString()} →{" "}
              {new Date(s.periodEnd).toLocaleDateString()}
            </CardTitle>
          </div>
          <p className="text-xs text-muted-foreground">
            Generated {new Date(s.generatedAt).toLocaleString()}
          </p>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#2563EB" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground">No numeric metrics.</p>
          )}
          <pre className="mt-4 max-h-96 overflow-auto rounded-md bg-muted p-3 text-xs">
            {JSON.stringify(s.metricsJson, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
