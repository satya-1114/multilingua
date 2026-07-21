import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/empty-state";
import { favoritesService, type FavoritePage } from "@/services/favorites.service";
import { formatDistanceToNow } from "date-fns";

export const Route = createFileRoute("/_authenticated/favorites")({
  head: () => ({ meta: [{ title: "Favorites" }, { name: "robots", content: "noindex" }] }),
  component: FavoritesPage,
});

function FavoritesPage() {
  const [items, setItems] = useState<FavoritePage[]>([]);
  useEffect(() => { setItems(favoritesService.list()); }, []);

  return (
    <div className="space-y-5">
        <SectionHeader
          title="Favorites"
          description="Quick access to your pinned pages."
          actions={
            <Button variant="outline" onClick={() => { favoritesService.clear(); setItems([]); }}>
              Clear all
            </Button>
          }
        />
        {items.length === 0 ? (
          <Card><CardContent className="p-8">
            <EmptyState title="Nothing pinned yet" description="Use the star in the top bar to pin the current page." />
          </CardContent></Card>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {items.map((f) => (
              <Card key={f.to}>
                <CardContent className="p-4">
                  <Link to={f.to} className="flex items-center gap-2 text-sm font-medium hover:underline">
                    <Star className="h-3.5 w-3.5 fill-current text-warning" />
                    {f.title}
                  </Link>
                  <p className="mt-1 text-xs text-muted-foreground">{f.to}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    Added {formatDistanceToNow(new Date(f.addedAt), { addSuffix: true })}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
  );
}
