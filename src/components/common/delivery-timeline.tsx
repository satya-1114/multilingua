import { CheckCircle2, Clock, Send, MailOpen, MousePointerClick, MessageSquare, Sparkles, XCircle, CalendarClock, ShieldCheck } from "lucide-react";
import { Timeline, type TimelineItem } from "@/components/common/timeline";
import type { CommunicationTimelineEvent } from "@/types/communication";

const ICONS = {
  created: Sparkles,
  approved: ShieldCheck,
  scheduled: CalendarClock,
  sent: Send,
  delivered: CheckCircle2,
  opened: MailOpen,
  clicked: MousePointerClick,
  responded: MessageSquare,
  completed: CheckCircle2,
  failed: XCircle,
} as const;

const TONES = {
  created: "primary", approved: "primary", scheduled: "accent", sent: "primary",
  delivered: "success", opened: "success", clicked: "accent", responded: "accent",
  completed: "success", failed: "warning",
} as const;

const LABELS = {
  created: "Campaign created", approved: "Approved", scheduled: "Scheduled",
  sent: "Sent to provider", delivered: "Delivered", opened: "Opened by recipient",
  clicked: "Link clicked", responded: "Response received", completed: "Completed", failed: "Failed",
} as const;

export function DeliveryTimeline({ events }: { events: CommunicationTimelineEvent[] }) {
  const items: TimelineItem[] = events.map((e) => ({
    id: e.id,
    title: LABELS[e.step],
    description: [e.actor, e.channel, e.note].filter(Boolean).join(" · ") || undefined,
    at: e.at,
    icon: (ICONS[e.step] ?? Clock),
    tone: TONES[e.step] as TimelineItem["tone"],
  }));
  return <Timeline items={items} />;
}
