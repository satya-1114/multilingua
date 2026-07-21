import { cn } from "@/lib/utils";
import type { Permission } from "@/constants/rbac";

interface PermissionBadgeProps {
  permission: Permission;
  className?: string;
}

export function PermissionBadge({ permission, className }: PermissionBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border border-border bg-card px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground",
        className,
      )}
    >
      {permission}
    </span>
  );
}
