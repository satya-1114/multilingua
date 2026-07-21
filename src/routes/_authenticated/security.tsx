import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { SectionHeader } from "@/components/common/section-header";
import { cn } from "@/lib/utils";

const links = [
  { to: "/security", label: "Overview" },
  { to: "/security/sessions", label: "Sessions & devices" },
  { to: "/security/policy", label: "Policies" },
] as const;

export const Route = createFileRoute("/_authenticated/security")({
  head: () => ({ meta: [{ title: "Security center" }, { name: "robots", content: "noindex" }] }),
  component: SecurityLayout,
});

function SecurityLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div className="space-y-5">
        <SectionHeader title="Security center" description="Sessions, alerts, and access policies." />
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
