import type { ReactNode } from "react";
import { Search, Filter, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DataTableToolbarProps {
  search: string;
  onSearchChange: (v: string) => void;
  onOpenFilters?: () => void;
  filterCount?: number;
  onClearFilters?: () => void;
  actions?: ReactNode;
  placeholder?: string;
  className?: string;
}

export function DataTableToolbar({
  search,
  onSearchChange,
  onOpenFilters,
  filterCount = 0,
  onClearFilters,
  actions,
  placeholder = "Search…",
  className,
}: DataTableToolbarProps) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <div className="relative flex-1 min-w-[200px]">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={placeholder}
          className="h-9 pl-9"
        />
      </div>
      {onOpenFilters && (
        <Button variant="outline" size="sm" onClick={onOpenFilters} className="gap-2">
          <Filter className="h-4 w-4" />
          Filters
          {filterCount > 0 && (
            <span className="ml-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
              {filterCount}
            </span>
          )}
        </Button>
      )}
      {filterCount > 0 && onClearFilters && (
        <Button variant="ghost" size="sm" onClick={onClearFilters} className="gap-1 text-muted-foreground">
          <X className="h-3.5 w-3.5" /> Clear
        </Button>
      )}
      {actions}
    </div>
  );
}
