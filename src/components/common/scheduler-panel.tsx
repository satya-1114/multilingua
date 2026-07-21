import { useMemo, useState, useEffect } from "react";
import { format } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertTriangle, CalendarClock } from "lucide-react";
import type { ScheduleConfig, ScheduleMode, RecurrencePattern, ScheduleConflict } from "@/types/scheduler";
import { schedulerService } from "@/services/scheduler.service";

const MODES: ScheduleMode[] = ["immediate", "scheduled", "recurring"];
const PATTERNS: RecurrencePattern[] = ["daily", "weekly", "monthly", "custom"];
const TIMEZONES = ["Asia/Kolkata", "UTC", "Asia/Dubai", "Europe/London", "America/New_York"];

interface Props {
  initial?: Partial<ScheduleConfig>;
  onSubmit: (cfg: ScheduleConfig) => void;
}

export function SchedulerPanel({ initial, onSubmit }: Props) {
  const [cfg, setCfg] = useState<ScheduleConfig>({
    id: initial?.id ?? `sch-${Date.now().toString(36)}`,
    campaignId: initial?.campaignId ?? "",
    campaignName: initial?.campaignName ?? "",
    mode: initial?.mode ?? "scheduled",
    timezone: initial?.timezone ?? "Asia/Kolkata",
    startAt: initial?.startAt ?? new Date(Date.now() + 60 * 60_000).toISOString(),
    endAt: initial?.endAt,
    recurrence: initial?.recurrence ?? { pattern: "weekly", interval: 1, daysOfWeek: [1] },
    createdAt: initial?.createdAt ?? new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  });
  const [conflicts, setConflicts] = useState<ScheduleConflict[]>([]);
  const [window, setWindow] = useState<{ start: string; end: string } | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [c, w] = await Promise.all([
        schedulerService.detectConflicts(cfg),
        schedulerService.estimateWindow(cfg),
      ]);
      if (alive) { setConflicts(c); setWindow(w); }
    })();
    return () => { alive = false; };
  }, [cfg]);

  const dtLocal = useMemo(() => (cfg.startAt ? format(new Date(cfg.startAt), "yyyy-MM-dd'T'HH:mm") : ""), [cfg.startAt]);

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Schedule</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label>Mode</Label>
            <div className="flex flex-wrap gap-2">
              {MODES.map((m) => (
                <button key={m} type="button" onClick={() => setCfg({ ...cfg, mode: m })}
                  className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset ${cfg.mode === m ? "bg-primary text-primary-foreground ring-primary" : "bg-muted text-muted-foreground ring-border"}`}>
                  {m}
                </button>
              ))}
            </div>
          </div>

          {cfg.mode !== "immediate" && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label>Start</Label>
                <Input type="datetime-local" value={dtLocal}
                  onChange={(e) => setCfg({ ...cfg, startAt: new Date(e.target.value).toISOString() })} />
              </div>
              <div className="grid gap-2">
                <Label>Timezone</Label>
                <Select value={cfg.timezone} onValueChange={(v) => setCfg({ ...cfg, timezone: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{TIMEZONES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
          )}

          {cfg.mode === "recurring" && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label>Pattern</Label>
                <Select value={cfg.recurrence?.pattern ?? "weekly"} onValueChange={(v) =>
                  setCfg({ ...cfg, recurrence: { ...(cfg.recurrence ?? { interval: 1 }), pattern: v as RecurrencePattern } })
                }>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{PATTERNS.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Interval</Label>
                <Input type="number" min={1} value={cfg.recurrence?.interval ?? 1}
                  onChange={(e) => setCfg({ ...cfg, recurrence: { ...(cfg.recurrence ?? { pattern: "weekly" }), interval: Number(e.target.value) || 1 } })} />
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <Button onClick={() => onSubmit(cfg)}>Save schedule</Button>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-sm"><CalendarClock className="h-4 w-4 text-primary" /> Estimated window</CardTitle></CardHeader>
          <CardContent className="text-sm">
            {window ? (
              <>
                <p className="font-medium">{format(new Date(window.start), "PPp")}</p>
                <p className="text-muted-foreground">to {format(new Date(window.end), "PPp")}</p>
              </>
            ) : <p className="text-muted-foreground">Calculating…</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-sm"><AlertTriangle className="h-4 w-4 text-amber-500" /> Conflict detection</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {conflicts.length === 0 ? (
              <p className="text-muted-foreground">No conflicts detected.</p>
            ) : (
              conflicts.map((c) => (
                <div key={c.scheduleId} className="rounded-lg bg-amber-500/10 px-3 py-2 text-amber-800 dark:text-amber-300">
                  <p className="font-medium">{c.campaignName}</p>
                  <p className="text-xs">{c.reason}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
