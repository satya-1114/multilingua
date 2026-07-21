import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { SectionHeader } from "@/components/common/section-header";
import { cn } from "@/lib/utils";

const links = [
  { to: "/monitoring", label: "Overview" },
  { to: "/monitoring/logs", label: "Logs" },
  { to: "/monitoring/health", label: "Health" },
] as const;

export const Route = createFileRoute("/_authenticated/monitoring")({
  head: () => ({ meta: [{ title: "Monitoring" }, { name: "robots", content: "noindex" }] }),
  component: MonitoringLayout,
});

function MonitoringLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div className="space-y-5">
        <SectionHeader title="Monitoring &amp; observability" description="Queues, service status, and application logs." />
        <nav className="flex flex-wrap gap-1 rounded-xl border bg-card p-1">
          {links.map((l) => {
            const active = pathname === l.to;
            return (
              <Link
                key={l.to}
                to={l.to}
                className={cn("rounded-lg px-3 py-1.5 text-sm font-medium", active ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent")}
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
