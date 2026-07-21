import type { ReactNode } from "react";
import { GripVertical, Star, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DashboardWidgetProps {
  title: string;
  description?: string;
  children: ReactNode;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  onHide?: () => void;
  onFavorite?: () => void;
  favorite?: boolean;
  className?: string;
}

export function DashboardWidget({
  title,
  description,
  children,
  onMoveUp,
  onMoveDown,
  onHide,
  onFavorite,
  favorite,
  className,
}: DashboardWidgetProps) {
  return (
    <Card className={cn("shadow-card", className)}>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-3">
        <div className="min-w-0">
          <CardTitle className="text-sm font-semibold">{title}</CardTitle>
          {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
        </div>
        <div className="flex items-center gap-0.5">
          {onFavorite && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onFavorite} aria-label="Favorite widget">
              <Star className={cn("h-3.5 w-3.5", favorite && "fill-current text-warning")} />
            </Button>
          )}
          {onMoveUp && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onMoveUp} aria-label="Move up">
              <GripVertical className="h-3.5 w-3.5" />
            </Button>
          )}
          {onHide && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onHide} aria-label="Hide widget">
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
