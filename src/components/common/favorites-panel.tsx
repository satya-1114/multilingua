import { Link } from "@tanstack/react-router";
import { Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/empty-state";
import { favoritesService } from "@/services/favorites.service";

export function FavoritesPanel() {
  const items = favoritesService.list();
  if (items.length === 0) {
    return (
      <Card className="shadow-card">
        <CardHeader>
          <CardTitle className="text-sm">Favorites</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="No favorites yet"
            description="Star pages from the header to keep them one click away."
          />
        </CardContent>
      </Card>
    );
  }
  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle className="text-sm">Favorites</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-1">
          {items.map((f) => (
            <li key={f.to}>
              <Link to={f.to} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-accent">
                <Star className="h-3.5 w-3.5 fill-current text-warning" />
                <span className="truncate">{f.title}</span>
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
