import { Mail, MessageSquare, MessageCircle, Bell, Globe, Share2, PhoneCall } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChannelKind } from "@/types/channel";

const META: Record<ChannelKind, { icon: LucideIcon; label: string; tone: string }> = {
  email: { icon: Mail, label: "Email", tone: "bg-blue-500/10 text-blue-700 dark:text-blue-300" },
  sms: { icon: MessageSquare, label: "SMS", tone: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" },
  whatsapp: { icon: MessageCircle, label: "WhatsApp", tone: "bg-green-600/10 text-green-700 dark:text-green-300" },
  push: { icon: Bell, label: "Push", tone: "bg-violet-500/10 text-violet-700 dark:text-violet-300" },
  web_broadcast: { icon: Globe, label: "Web", tone: "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300" },
  social_broadcast: { icon: Share2, label: "Social", tone: "bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300" },
  voice: { icon: PhoneCall, label: "Voice", tone: "bg-amber-500/10 text-amber-700 dark:text-amber-300" },
};

export function ChannelBadge({ channel, className, showLabel = true }: { channel: ChannelKind; className?: string; showLabel?: boolean }) {
  const { icon: Icon, label, tone } = META[channel];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ring-border/60", tone, className)}>
      <Icon className="h-3 w-3" />
      {showLabel && label}
    </span>
  );
}

export function channelLabel(k: ChannelKind) { return META[k].label; }
