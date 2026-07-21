import type { LucideIcon } from "lucide-react";
import { Bell, CheckCircle2, Clock3, GitBranch, Mail, MessageSquare, Sparkles, Timer, Users, Workflow as WorkflowIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { WorkflowNodeKind } from "@/types/automation";

interface WorkflowNodeCardProps {
  kind: WorkflowNodeKind;
  title: string;
  description?: string;
  selected?: boolean;
  onClick?: () => void;
  style?: React.CSSProperties;
  className?: string;
}

const meta: Record<WorkflowNodeKind, { icon: LucideIcon; color: string; label: string }> = {
  trigger:       { icon: WorkflowIcon,   color: "#2563EB", label: "Trigger" },
  approval:      { icon: CheckCircle2,   color: "#8B5CF6", label: "Approval" },
  delay:         { icon: Clock3,         color: "#94A3B8", label: "Delay" },
  condition:     { icon: GitBranch,      color: "#F59E0B", label: "Condition" },
  audience:      { icon: Users,          color: "#0EA5E9", label: "Audience" },
  template:      { icon: Mail,           color: "#22C55E", label: "Template" },
  communication: { icon: MessageSquare,  color: "#2563EB", label: "Send" },
  notification:  { icon: Bell,           color: "#DC2626", label: "Notify" },
  ai:            { icon: Sparkles,       color: "#8B5CF6", label: "AI" },
  end:           { icon: Timer,          color: "#0F172A", label: "End" },
};

export function WorkflowNodeCard({ kind, title, description, selected, onClick, style, className }: WorkflowNodeCardProps) {
  const m = meta[kind];
  const Icon = m.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      style={style}
      className={cn(
        "absolute w-44 rounded-xl border bg-card p-3 text-left shadow-card transition-all hover:shadow-elevated",
        selected ? "ring-2 ring-primary" : "border-border",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <div
          className="flex h-7 w-7 items-center justify-center rounded-md text-white"
          style={{ background: m.color }}
        >
          <Icon className="h-3.5 w-3.5" />
        </div>
        <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{m.label}</div>
      </div>
      <p className="mt-2 text-sm font-medium leading-snug">{title}</p>
      {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
    </button>
  );
}

export { meta as workflowNodeMeta };
