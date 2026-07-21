import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { SectionHeader } from "@/components/common/section-header";
import { cn } from "@/lib/utils";

/**
 * Translations platform layout — shared header + tab nav across the
 * translations, jobs and locales child routes.
 */
export const Route = createFileRoute("/_authenticated/translations")({
  head: () => ({
    meta: [
      { title: "Translations — Multilingua" },
      { name: "description", content: "Manage multilingual content translations, jobs and locales." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: TranslationsLayout,
});

const links = [
  { to: "/translations", label: "Translations", exact: true },
  { to: "/translations/jobs", label: "Jobs", exact: false },
  { to: "/translations/locales", label: "Locales", exact: false },
] as const;

function TranslationsLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="space-y-5">
      <SectionHeader
        title="Multilingual content"
        description="Manage per-entity translations, translation jobs and supported locales."
      />
      <nav className="flex flex-wrap items-center gap-1 rounded-xl border bg-card p-1">
        {links.map((l) => {
          const active = l.exact
            ? pathname === l.to || pathname === `${l.to}/`
            : pathname === l.to || pathname.startsWith(`${l.to}/`);
          return (
            <Link
              key={l.to}
              to={l.to}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent",
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
