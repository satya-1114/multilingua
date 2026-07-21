import { Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Mail, MessageSquare, Bell, Globe2, Radio, Megaphone, ShieldAlert, GraduationCap, Building2, Landmark, Sparkles, FileText, type LucideIcon } from "lucide-react";
import type { CommunicationTemplate, TemplateCategory } from "@/types/template";
import { TEMPLATE_CATEGORY_META } from "@/constants/template";
import { cn } from "@/lib/utils";

const CATEGORY_ICON: Record<TemplateCategory, LucideIcon> = {
  email: Mail,
  sms: MessageSquare,
  whatsapp: MessageSquare,
  push: Bell,
  banner: Globe2,
  social: Radio,
  emergency_alert: ShieldAlert,
  government_notice: Landmark,
  healthcare: Sparkles,
  education: GraduationCap,
  internal: Building2,
  custom: FileText,
};

interface Props {
  template: CommunicationTemplate;
  index?: number;
}

export function TemplateCard({ template, index = 0 }: Props) {
  const Icon = CATEGORY_ICON[template.category] ?? Megaphone;
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 10) * 0.02 }}
      className="group relative overflow-hidden rounded-xl border bg-card p-4 shadow-card transition-shadow hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <Link
              to="/templates/$id"
              params={{ id: template.id }}
              className="block truncate text-sm font-semibold text-foreground hover:text-primary"
            >
              {template.name}
            </Link>
            <p className="text-xs text-muted-foreground">
              {TEMPLATE_CATEGORY_META[template.category].label} · {template.language.toUpperCase()} · v{template.version}
            </p>
          </div>
        </div>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ring-1 ring-inset",
            template.status === "published"
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-emerald-500/20"
              : template.status === "draft"
                ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-amber-500/20"
                : "bg-slate-500/10 text-slate-600 dark:text-slate-300 ring-slate-500/20",
          )}
        >
          {template.status}
        </span>
      </div>
      <p className="mt-3 line-clamp-3 text-sm text-muted-foreground">{template.body}</p>
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>Used {template.usageCount} times</span>
        <span>Updated {new Date(template.updatedAt).toLocaleDateString()}</span>
      </div>
    </motion.div>
  );
}
