import { createFileRoute, Link, Outlet } from "@tanstack/react-router";
import { Workflow, LayoutDashboard, ListChecks, PlayCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/workflows")({
  head: () => ({
    meta: [
      { title: "Automation & Workflows" },
      { name: "description", content: "Design, monitor, and operate automation workflows." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: WorkflowsLayout,
});

const TABS: ReadonlyArray<{
  to: "/workflows" | "/workflows/definitions" | "/workflows/executions";
  label: string;
  icon: typeof LayoutDashboard;
  exact?: boolean;
}> = [
  { to: "/workflows", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { to: "/workflows/definitions", label: "Definitions", icon: ListChecks },
  { to: "/workflows/executions", label: "Executions", icon: PlayCircle },
];

function WorkflowsLayout() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Workflow className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold">Automation &amp; Workflow Engine</h1>
      </div>
      <nav className="flex flex-wrap gap-1 border-b border-border">
        {TABS.map((t) => (
          <Link
            key={t.to}
            to={t.to}
            activeOptions={{ exact: t.exact }}
            className={cn(
              "flex items-center gap-1.5 border-b-2 border-transparent px-3 py-2 text-sm text-muted-foreground",
              "hover:text-foreground",
            )}
            activeProps={{
              className:
                "flex items-center gap-1.5 border-b-2 border-primary px-3 py-2 text-sm text-foreground font-medium",
            }}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </Link>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
