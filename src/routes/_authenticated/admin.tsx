import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { SectionHeader } from "@/components/common/section-header";
import { cn } from "@/lib/utils";

const links = [
  { to: "/admin", label: "Overview" },
  { to: "/admin/readiness", label: "Readiness" },
  { to: "/admin/feature-flags", label: "Feature flags" },
  { to: "/admin/platform", label: "Platform config" },
  { to: "/admin/health", label: "System health" },
  { to: "/admin/license", label: "License" },
] as const;

export const Route = createFileRoute("/_authenticated/admin")({
  head: () => ({ meta: [{ title: "Administration" }, { name: "robots", content: "noindex" }] }),
  component: AdminLayout,
});

function AdminLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div className="space-y-5">
        <SectionHeader title="Administration" description="Manage platform-wide configuration and observability." />
        <nav className="flex flex-wrap items-center gap-1 rounded-xl border bg-card p-1">
          {links.map((l) => {
            const active = pathname === l.to || (l.to === "/admin" && pathname === "/admin");
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
