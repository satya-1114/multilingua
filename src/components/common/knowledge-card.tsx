import { Card, CardContent } from "@/components/ui/card";
import type { KnowledgeArticle } from "@/types/help";
import { formatDistanceToNow } from "date-fns";
import { BookOpen, Clock3 } from "lucide-react";

export function KnowledgeCard({ article }: { article: KnowledgeArticle }) {
  return (
    <Card className="shadow-card transition-shadow hover:shadow-elevated">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <BookOpen className="h-3.5 w-3.5" />
          <span>{article.category}</span>
          <span aria-hidden>·</span>
          <Clock3 className="h-3.5 w-3.5" />
          <span>{article.readMinutes} min read</span>
        </div>
        <h3 className="mt-2 text-sm font-semibold">{article.title}</h3>
        <p className="mt-1 text-sm text-muted-foreground">{article.excerpt}</p>
        <p className="mt-3 text-[11px] text-muted-foreground">
          Updated {formatDistanceToNow(new Date(article.updatedAt), { addSuffix: true })}
        </p>
      </CardContent>
    </Card>
  );
}
