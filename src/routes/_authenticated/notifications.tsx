import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import { motion } from "framer-motion";
import { Archive, Check, CheckCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SectionHeader } from "@/components/common/section-header";
import { SearchBar } from "@/components/common/search-bar";
import { FilterDropdown } from "@/components/common/filter-dropdown";
import { EmptyState } from "@/components/common/empty-state";
import { StatusChip } from "@/components/common/status-chip";
import { useNotifications } from "@/contexts/notification-context";
import { cn } from "@/lib/utils";
import type {
  AppNotification,
  NotificationCategory,
  NotificationPriority,
} from "@/types/notification";

export const Route = createFileRoute("/_authenticated/notifications")({
  head: () => ({
    meta: [
      { title: "Notifications — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: NotificationsPage,
});

const priorityTone: Record<NotificationPriority, "muted" | "info" | "warning" | "danger"> = {
  low: "muted",
  normal: "info",
  high: "warning",
  critical: "danger",
};

const categoryLabels: Record<NotificationCategory, string> = {
  campaign: "Campaigns",
  system: "System",
  team: "Team",
  billing: "Billing",
  security: "Security",
};

type ReadFilter = "all" | "unread" | "read";
type CategoryFilter = NotificationCategory | "all";

function NotificationsPage() {
  const { notifications, markRead, markAllRead, archive, unreadCount } = useNotifications();
  const [query, setQuery] = useState("");
  const [readFilter, setReadFilter] = useState<ReadFilter>("all");
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [showArchived, setShowArchived] = useState(false);

  const filtered = useMemo(() => {
    return notifications
      .filter((n) => (showArchived ? n.archived : !n.archived))
      .filter((n) => (category === "all" ? true : n.category === category))
      .filter((n) => {
        if (readFilter === "unread") return !n.read;
        if (readFilter === "read") return n.read;
        return true;
      })
      .filter((n) => {
        if (!query) return true;
        const q = query.toLowerCase();
        return (
          n.title.toLowerCase().includes(q) ||
          n.message.toLowerCase().includes(q) ||
          (n.actor?.toLowerCase().includes(q) ?? false)
        );
      });
  }, [notifications, showArchived, category, readFilter, query]);

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Notifications"
        description={
          unreadCount === 0
            ? "You're all caught up."
            : `${unreadCount} unread notification${unreadCount === 1 ? "" : "s"}.`
        }
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={markAllRead}
            disabled={unreadCount === 0}
            className="gap-2"
          >
            <CheckCheck className="h-3.5 w-3.5" /> Mark all read
          </Button>
        }
      />

      <Card className="shadow-card">
        <CardContent className="space-y-4 p-4 md:p-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <SearchBar value={query} onChange={setQuery} placeholder="Search notifications…" className="sm:w-72" />
            <div className="flex flex-wrap items-center gap-2">
              <FilterDropdown
                label="Status"
                value={readFilter}
                onChange={(v) => setReadFilter(v as ReadFilter)}
                options={[
                  { value: "all", label: "All" },
                  { value: "unread", label: "Unread" },
                  { value: "read", label: "Read" },
                ]}
              />
              <FilterDropdown
                label="Category"
                value={category}
                onChange={(v) => setCategory(v as CategoryFilter)}
                options={[
                  { value: "all", label: "All categories" },
                  ...Object.entries(categoryLabels).map(([value, label]) => ({ value, label })),
                ]}
              />
              <Button
                variant={showArchived ? "default" : "outline"}
                size="sm"
                onClick={() => setShowArchived((v) => !v)}
                className="gap-2"
              >
                <Archive className="h-3.5 w-3.5" />
                {showArchived ? "Viewing archive" : "Show archive"}
              </Button>
            </div>
          </div>

          {filtered.length === 0 ? (
            <EmptyState
              title="No notifications"
              description="Try changing your filters or check back later."
            />
          ) : (
            <ul className="divide-y divide-border">
              {filtered.map((n, i) => (
                <NotificationRow
                  key={n.id}
                  n={n}
                  index={i}
                  onRead={() => markRead(n.id)}
                  onArchive={() => archive(n.id)}
                />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

interface NotificationRowProps {
  n: AppNotification;
  index: number;
  onRead: () => void;
  onArchive: () => void;
}

function NotificationRow({ n, index, onRead, onArchive }: NotificationRowProps) {
  return (
    <motion.li
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.02, 0.15) }}
      className={cn("flex items-start gap-3 py-3", !n.read && "bg-primary/[.03]")}
    >
      <span
        className={cn(
          "mt-2 h-2 w-2 shrink-0 rounded-full",
          n.read ? "bg-transparent" : "bg-primary",
        )}
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-foreground">{n.title}</p>
          <StatusChip label={n.priority} tone={priorityTone[n.priority]} />
          <StatusChip label={categoryLabels[n.category]} tone="muted" />
        </div>
        <p className="mt-0.5 text-sm text-muted-foreground">{n.message}</p>
        <p className="mt-1 text-[11px] text-muted-foreground">
          {formatDistanceToNow(new Date(n.timestamp), { addSuffix: true })}
          {n.actor ? ` · by ${n.actor}` : ""}
        </p>
      </div>
      <div className="flex items-center gap-1">
        {!n.read && (
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onRead} aria-label="Mark read">
            <Check className="h-3.5 w-3.5" />
          </Button>
        )}
        {!n.archived && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={onArchive}
            aria-label="Archive"
          >
            <Archive className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </motion.li>
  );
}
