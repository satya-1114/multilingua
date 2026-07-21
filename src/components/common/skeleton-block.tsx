import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonBlockProps {
  rows?: number;
  className?: string;
}

export function SkeletonBlock({ rows = 3, className }: SkeletonBlockProps) {
  return (
    <div className={className}>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" />
        ))}
      </div>
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-card">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-3 h-6 w-32" />
      <Skeleton className="mt-3 h-3 w-40" />
    </div>
  );
}
