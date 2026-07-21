import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { SectionHeader } from "@/components/common/section-header";
import { cn } from "@/lib/utils";

const links = [
  { to: "/communication", label: "Overview" },
  { to: "/communication/channels", label: "Channels" },
  { to: "/communication/delivery", label: "Delivery" },
  { to: "/communication/scheduling", label: "Scheduling" },
  { to: "/communication/retry-policies", label: "Retry policies" },
  { to: "/communication/engagement", label: "Engagement" },
] as const;

export const Route = createFileRoute("/_authenticated/communication")({
  head: () => ({ meta: [{ title: "Communication Center" }, { name: "robots", content: "noindex" }] }),
  component: CommunicationLayout,
});

function CommunicationLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div className="space-y-5">
        <SectionHeader
          title="Communication Center"
          description="Multi-channel delivery, scheduling, and engagement across every campaign."
        />
        <nav className="flex flex-wrap gap-1 rounded-xl border bg-card p-1">
          {links.map((l) => {
            const active = l.to === "/communication" ? pathname === l.to : pathname.startsWith(l.to);
            return (
              <Link
                key={l.to}
                to={l.to}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
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
