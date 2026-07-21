import { Star, Copy, Trash2, PenSquare } from "lucide-react";
import { motion } from "framer-motion";
import type { PromptTemplate } from "@/types/ai";
import { PROMPT_CATEGORIES } from "@/constants/ai";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PromptCardProps {
  prompt: PromptTemplate;
  onToggleFavorite?: (prompt: PromptTemplate) => void;
  onDuplicate?: (prompt: PromptTemplate) => void;
  onEdit?: (prompt: PromptTemplate) => void;
  onDelete?: (prompt: PromptTemplate) => void;
  onUse?: (prompt: PromptTemplate) => void;
}

export function PromptCard({
  prompt,
  onToggleFavorite,
  onDuplicate,
  onEdit,
  onDelete,
  onUse,
}: PromptCardProps) {
  const category = PROMPT_CATEGORIES.find((c) => c.key === prompt.category);
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
    >
      <Card className="h-full transition-shadow hover:shadow-elevated">
        <CardContent className="flex h-full flex-col gap-3 p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-foreground">
                {prompt.title}
              </p>
              <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                {prompt.description}
              </p>
            </div>
            <button
              type="button"
              onClick={() => onToggleFavorite?.(prompt)}
              aria-label={prompt.favorite ? "Unfavorite" : "Favorite"}
              className="rounded-md p-1 text-muted-foreground hover:text-warning"
            >
              <Star
                className={cn(
                  "h-4 w-4",
                  prompt.favorite && "fill-warning text-warning",
                )}
              />
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {category && (
              <Badge variant="secondary" className="text-[10px]">
                {category.label}
              </Badge>
            )}
            {prompt.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-md bg-muted/60 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground"
              >
                #{tag}
              </span>
            ))}
          </div>

          <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-2 font-mono text-[11px] leading-relaxed text-muted-foreground">
            {prompt.body.length > 160 ? `${prompt.body.slice(0, 160)}…` : prompt.body}
          </div>

          <div className="mt-auto flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Used {prompt.usageCount}×</span>
            <div className="flex items-center gap-1">
              {onEdit && (
                <Button size="icon" variant="ghost" onClick={() => onEdit(prompt)} aria-label="Edit">
                  <PenSquare className="h-3.5 w-3.5" />
                </Button>
              )}
              {onDuplicate && (
                <Button size="icon" variant="ghost" onClick={() => onDuplicate(prompt)} aria-label="Duplicate">
                  <Copy className="h-3.5 w-3.5" />
                </Button>
              )}
              {onDelete && (
                <Button size="icon" variant="ghost" onClick={() => onDelete(prompt)} aria-label="Delete">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
              {onUse && (
                <Button size="sm" variant="secondary" onClick={() => onUse(prompt)}>
                  Use
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
