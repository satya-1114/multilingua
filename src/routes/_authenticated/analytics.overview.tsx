import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  Building2,
  FileBarChart,
  Flame,
  Globe2,
  Languages,
  Users,
} from "lucide-react";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { analyticsService } from "@/services/analytics.service";
import { queryKeys } from "@/lib/queryKeys";
import { usePermissions } from "@/hooks/use-permissions";
import { PERMISSIONS } from "@/constants/rbac";

export const Route = createFileRoute("/_authenticated/analytics/overview")({
  head: () => ({
    meta: [
      { title: "Platform overview — Analytics" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: PlatformOverviewPage,
});

function PlatformOverviewPage() {
  const { hasPermission } = usePermissions();
  const canView = hasPermission(PERMISSIONS.ANALYTICS_VIEW);

  const q = useQuery({
    queryKey: queryKeys.analytics.platformOverview(),
    queryFn: () => analyticsService.platformOverview(),
    enabled: canView,
  });

  if (!canView) {
    return (
      <Alert>
        <AlertTitle>Analytics access required</AlertTitle>
        <AlertDescription>You do not have permission to view platform analytics.</AlertDescription>
      </Alert>
    );
  }

  if (q.isLoading) {
    return (
      <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    );
  }

  if (q.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load overview</AlertTitle>
        <AlertDescription>{(q.error as Error)?.message ?? "Unknown error"}</AlertDescription>
      </Alert>
    );
  }

  const d = q.data!;
  const cards = [
    { label: "Total volunteers", value: d.totalVolunteers, icon: Users },
    { label: "Active disasters", value: d.activeDisasters, icon: Flame },
    { label: "Public resources", value: d.publicResources, icon: Globe2 },
    { label: "Published translations", value: d.publishedTranslations, icon: Languages },
    { label: "Organizations", value: d.organizations, icon: Building2 },
    { label: "Reports generated", value: d.reportsGenerated, icon: FileBarChart },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
        {cards.map((c) => (
          <AnalyticsCard key={c.label} label={c.label} value={c.value} icon={c.icon} />
        ))}
      </div>
      <p className="flex items-center gap-2 text-xs text-muted-foreground">
        <BarChart3 className="h-3.5 w-3.5" />
        Live platform KPIs — refreshes on navigation.
      </p>
    </div>
  );
}
