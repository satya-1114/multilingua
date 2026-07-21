import { ROLE_METADATA, type Role } from "@/constants/rbac";
import { cn } from "@/lib/utils";

const toneClasses: Record<string, string> = {
  primary: "bg-primary/10 text-primary",
  accent: "bg-accent/15 text-accent",
  warning: "bg-warning/15 text-warning-foreground",
  muted: "bg-muted text-muted-foreground",
};

interface RoleBadgeProps {
  role: Role;
  className?: string;
}

export function RoleBadge({ role, className }: RoleBadgeProps) {
  const meta = ROLE_METADATA[role];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold",
        toneClasses[meta.tone],
        className,
      )}
    >
      {meta.label}
    </span>
  );
}
