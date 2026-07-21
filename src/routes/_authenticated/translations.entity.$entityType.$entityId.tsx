import { createFileRoute } from "@tanstack/react-router";
import { EntityTranslationsPanel } from "@/components/translations/entity-translations-panel";

/**
 * Reusable entity-scoped translations page:
 *   /translations/entity/:entityType/:entityId
 *
 * Deep-linkable from Disaster / Public Resource / Organization / Campaign
 * detail pages that need a full multilingual view for one entity.
 */
export const Route = createFileRoute(
  "/_authenticated/translations/entity/$entityType/$entityId",
)({
  head: () => ({
    meta: [
      { title: "Entity translations — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: EntityTranslationsPage,
});

function EntityTranslationsPage() {
  const { entityType, entityId } = Route.useParams();
  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-sm">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">Entity</p>
        <p className="capitalize">{entityType.replace(/_/g, " ")}</p>
        <p className="mt-1 font-mono text-xs text-muted-foreground">{entityId}</p>
      </div>
      <EntityTranslationsPanel entityType={entityType} entityId={entityId} />
    </div>
  );
}
