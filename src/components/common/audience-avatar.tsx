import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface AudienceAvatarProps {
  name: string;
  src?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZES = {
  sm: "h-8 w-8 text-[11px]",
  md: "h-10 w-10 text-sm",
  lg: "h-16 w-16 text-lg",
};

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

function toneFor(name: string): string {
  const palette = [
    "bg-primary/10 text-primary",
    "bg-accent/10 text-accent",
    "bg-emerald-500/10 text-emerald-600",
    "bg-amber-500/10 text-amber-600",
    "bg-violet-500/10 text-violet-600",
    "bg-rose-500/10 text-rose-600",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return palette[hash % palette.length]!;
}

export function AudienceAvatar({ name, src, size = "md", className }: AudienceAvatarProps) {
  return (
    <Avatar className={cn(SIZES[size], className)}>
      {src && <AvatarImage src={src} alt={name} />}
      <AvatarFallback className={cn("font-semibold", toneFor(name))}>{initials(name) || "?"}</AvatarFallback>
    </Avatar>
  );
}
