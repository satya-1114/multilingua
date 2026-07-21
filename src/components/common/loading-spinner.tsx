import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

const sizes = { sm: "h-3.5 w-3.5", md: "h-4 w-4", lg: "h-5 w-5" };

export function LoadingSpinner({ size = "md", className, label }: LoadingSpinnerProps) {
  return (
    <span className="inline-flex items-center gap-2 text-muted-foreground" role="status">
      <Loader2 className={cn("animate-spin", sizes[size], className)} />
      {label && <span className="text-sm">{label}</span>}
    </span>
  );
}
