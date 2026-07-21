import { cn } from "@/lib/utils";

type Tone = "success" | "warning" | "danger" | "info" | "muted" | "accent";

const toneClasses: Record<Tone, string> = {
  success: "bg-success/12 text-success",
  warning: "bg-warning/15 text-warning-foreground",
  danger: "bg-destructive/12 text-destructive",
  info: "bg-primary/12 text-primary",
  accent: "bg-accent/15 text-accent",
  muted: "bg-muted text-muted-foreground",
};

interface StatusChipProps {
  label: string;
  tone?: Tone;
  className?: string;
}

export function StatusChip({ label, tone = "muted", className }: StatusChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
        toneClasses[tone],
        className,
      )}
    >
      <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}

export function statusChipToneFor(
  status: "draft" | "scheduled" | "running" | "completed" | "paused",
): Tone {
  switch (status) {
    case "running":
      return "success";
    case "scheduled":
      return "info";
    case "draft":
      return "muted";
    case "completed":
      return "accent";
    case "paused":
      return "warning";
  }
}
