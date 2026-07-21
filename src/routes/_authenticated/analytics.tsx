import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { SectionHeader } from "@/components/common/section-header";
import { cn } from "@/lib/utils";

const links = [
  { to: "/analytics", label: "Executive overview" },
  { to: "/analytics/overview", label: "Platform overview" },
  { to: "/analytics/platform", label: "Platform" },
  { to: "/analytics/metrics", label: "Metrics" },
  { to: "/analytics/snapshots", label: "Snapshots" },
  { to: "/analytics/jobs", label: "Report jobs" },
  { to: "/analytics/reports", label: "Reports" },
  { to: "/analytics/builder", label: "Report builder" },
] as const;

export const Route = createFileRoute("/_authenticated/analytics")({
  head: () => ({ meta: [{ title: "Analytics" }, { name: "robots", content: "noindex" }] }),
  component: AnalyticsLayout,
});

function AnalyticsLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div className="space-y-5">
        <SectionHeader title="Analytics" description="Executive metrics, delivery insights, and custom reporting." />
        <nav className="flex flex-wrap gap-1 rounded-xl border bg-card p-1">
          {links.map((l) => {
            const active = pathname === l.to;
            return (
              <Link
                key={l.to}
                to={l.to}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-sm font-medium",
                  active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent",
                )}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <Outlet />
      </div>
  );
}
