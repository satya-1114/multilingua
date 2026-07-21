import type { ScheduleConfig, ScheduleConflict } from "@/types/scheduler";
import { mockSchedules } from "@/lib/mock/communication";

const delay = <T>(v: T, ms = 200): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let store: ScheduleConfig[] = [...mockSchedules];

export const schedulerService = {
  async list(): Promise<ScheduleConfig[]> { return delay([...store]); },
  async get(id: string): Promise<ScheduleConfig | null> { return delay(store.find((s) => s.id === id) ?? null); },
  async upsert(cfg: ScheduleConfig): Promise<ScheduleConfig> {
    const idx = store.findIndex((s) => s.id === cfg.id);
    const rec: ScheduleConfig = { ...cfg, updatedAt: new Date().toISOString() };
    if (idx >= 0) store[idx] = rec; else store = [rec, ...store];
    return delay(rec);
  },
  async remove(id: string) {
    store = store.filter((s) => s.id !== id);
    return delay({ ok: true });
  },
  async detectConflicts(cfg: ScheduleConfig): Promise<ScheduleConflict[]> {
    const conflicts: ScheduleConflict[] = [];
    const start = cfg.startAt ? new Date(cfg.startAt).getTime() : 0;
    for (const other of store) {
      if (other.id === cfg.id || !other.startAt) continue;
      const otherStart = new Date(other.startAt).getTime();
      if (Math.abs(otherStart - start) < 30 * 60 * 1000) {
        conflicts.push({
          scheduleId: other.id,
          campaignName: other.campaignName,
          reason: `Overlaps with ${other.campaignName} within 30 minutes.`,
          severity: "warning",
        });
      }
    }
    return delay(conflicts);
  },
  async estimateWindow(cfg: ScheduleConfig): Promise<{ start: string; end: string }> {
    const start = cfg.startAt ?? new Date().toISOString();
    const durationMs = 90 * 60 * 1000;
    return delay({ start, end: new Date(new Date(start).getTime() + durationMs).toISOString() });
  },
};
