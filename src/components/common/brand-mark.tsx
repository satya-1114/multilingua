import { Languages } from "lucide-react";
import { APP_NAME } from "@/constants/navigation";

interface BrandMarkProps {
  compact?: boolean;
}

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-card">
        <Languages className="h-5 w-5" />
      </div>
      {!compact && (
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold text-foreground">{APP_NAME}</span>
          <span className="text-[11px] font-medium text-muted-foreground">Platform</span>
        </div>
      )}
    </div>
  );
}
