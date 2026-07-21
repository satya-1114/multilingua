import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Campaign } from "@/types/campaign";
import { cn } from "@/lib/utils";

interface Props {
  campaigns: Campaign[];
  className?: string;
}

const WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function startOfMonthGrid(d: Date): Date {
  const first = new Date(d.getFullYear(), d.getMonth(), 1);
  const offset = (first.getDay() + 6) % 7; // Monday-first
  first.setDate(first.getDate() - offset);
  return first;
}

export function CampaignCalendar({ campaigns, className }: Props) {
  const [cursor, setCursor] = useState(() => new Date());

  const byDay = useMemo(() => {
    const map = new Map<string, Campaign[]>();
    campaigns.forEach((c) => {
      const start = c.schedule.startAt ? new Date(c.schedule.startAt) : null;
      if (!start) return;
      const key = start.toISOString().slice(0, 10);
      const list = map.get(key) ?? [];
      list.push(c);
      map.set(key, list);
    });
    return map;
  }, [campaigns]);

  const gridStart = startOfMonthGrid(cursor);
  const days: Date[] = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(gridStart);
    d.setDate(d.getDate() + i);
    return d;
  });

  const monthLabel = cursor.toLocaleDateString("en", { month: "long", year: "numeric" });

  return (
    <div className={cn("rounded-xl border bg-card shadow-card", className)}>
      <div className="flex items-center justify-between border-b px-4 py-3">
        <p className="text-sm font-semibold text-foreground">{monthLabel}</p>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCursor((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))}
            aria-label="Previous month"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setCursor(new Date())}>
            Today
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCursor((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))}
            aria-label="Next month"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-7 gap-px bg-border">
        {WEEK.map((w) => (
          <div key={w} className="bg-muted/60 px-2 py-1.5 text-center text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            {w}
          </div>
        ))}
        {days.map((day, idx) => {
          const inMonth = day.getMonth() === cursor.getMonth();
          const isToday = day.toDateString() === new Date().toDateString();
          const key = day.toISOString().slice(0, 10);
          const events = byDay.get(key) ?? [];
          return (
            <div
              key={idx}
              className={cn(
                "min-h-[92px] bg-card p-1.5 text-xs",
                !inMonth && "bg-muted/20 text-muted-foreground",
              )}
            >
              <div className="flex items-center justify-between">
                <span className={cn("text-xs font-medium", isToday && "flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground")}>
                  {day.getDate()}
                </span>
              </div>
              <div className="mt-1 flex flex-col gap-1">
                {events.slice(0, 3).map((c) => (
                  <Link
                    key={c.id}
                    to="/campaigns/$id"
                    params={{ id: c.id }}
                    className="truncate rounded-md px-1.5 py-0.5 text-[10px] font-medium text-white hover:opacity-90"
                    style={{ background: c.color }}
                    title={c.name}
                  >
                    {c.name}
                  </Link>
                ))}
                {events.length > 3 && (
                  <span className="text-[10px] text-muted-foreground">+{events.length - 3} more</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
