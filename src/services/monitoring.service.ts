import type { ServiceStatus, QueueSnapshot, HealthMetric, LogEntry } from "@/types/monitoring";
import { mockServices, mockQueues, mockHealth, mockLogs } from "@/lib/mock/platform";

const delay = <T>(v: T, ms = 220): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

export const monitoringService = {
  async services(): Promise<ServiceStatus[]> { return delay([...mockServices]); },
  async queues(): Promise<QueueSnapshot[]> { return delay([...mockQueues]); },
  async health(): Promise<HealthMetric[]> { return delay([...mockHealth]); },
  async logs(query: { level?: LogEntry["level"] | "all"; search?: string; service?: string } = {}): Promise<LogEntry[]> {
    let out = [...mockLogs];
    if (query.level && query.level !== "all") out = out.filter((l) => l.level === query.level);
    if (query.service) out = out.filter((l) => l.service === query.service);
    if (query.search) {
      const q = query.search.toLowerCase();
      out = out.filter((l) => l.message.toLowerCase().includes(q) || (l.actor ?? "").includes(q));
    }
    return delay(out);
  },
};
