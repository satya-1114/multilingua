import type {
  DeliveryActionResult,
  DeliveryJob,
  DeliveryListQuery,
  DeliveryQueueSnapshot,
  DeliveryRecipient,
  DeliveryStatus,
} from "@/types/delivery";
import { mockDeliveryJobs, mockQueueSnapshots, mockRecipients } from "@/lib/mock/communication";

const delay = <T>(v: T, ms = 220): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));
let store: DeliveryJob[] = mockDeliveryJobs.map((j) => ({ ...j }));

function apply(q: DeliveryListQuery): DeliveryJob[] {
  let items = [...store];
  if (q.search) {
    const s = q.search.toLowerCase();
    items = items.filter((j) => j.campaignName.toLowerCase().includes(s) || j.id.toLowerCase().includes(s));
  }
  if (q.status?.length) items = items.filter((j) => q.status!.includes(j.status));
  if (q.channel?.length) items = items.filter((j) => q.channel!.includes(j.channel));
  if (q.priority?.length) items = items.filter((j) => q.priority!.includes(j.priority));
  if (q.campaignId) items = items.filter((j) => j.campaignId === q.campaignId);
  return items.sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
}

function set(id: string, status: DeliveryStatus): DeliveryActionResult {
  const idx = store.findIndex((j) => j.id === id);
  if (idx < 0) return { ok: false, message: "Job not found" };
  store[idx] = { ...store[idx]!, status, updatedAt: new Date().toISOString() };
  return { ok: true, message: `Job ${id} → ${status}` };
}

export const deliveryService = {
  async list(query: DeliveryListQuery = {}): Promise<{ items: DeliveryJob[]; total: number }> {
    const items = apply(query);
    return delay({ items, total: items.length });
  },
  async queues(): Promise<DeliveryQueueSnapshot[]> {
    // rebuild from current store snapshot
    const snap = mockQueueSnapshots.map((s) => ({
      ...s,
      jobs: store.filter((j) => {
        if (s.kind === "delivery") return j.status === "queued";
        if (s.kind === "scheduled") return j.status === "scheduled";
        if (s.kind === "retry") return j.status === "retrying";
        if (s.kind === "failed") return j.status === "failed";
        if (s.kind === "processing") return j.status === "processing";
        if (s.kind === "cancelled") return j.status === "cancelled";
        if (s.kind === "completed") return j.status === "delivered";
        return false;
      }),
    })).map((s) => ({ ...s, count: s.jobs.length }));
    return delay(snap);
  },
  async recipients(campaignId?: string): Promise<DeliveryRecipient[]> {
    void campaignId;
    return delay(mockRecipients);
  },
  async retry(id: string) { return delay(set(id, "retrying")); },
  async cancel(id: string) { return delay(set(id, "cancelled")); },
  async pause(id: string) { return delay(set(id, "paused")); },
  async resume(id: string) { return delay(set(id, "processing")); },
  async prioritize(id: string) {
    const idx = store.findIndex((j) => j.id === id);
    if (idx < 0) return delay({ ok: false, message: "Not found" } as DeliveryActionResult);
    store[idx] = { ...store[idx]!, priority: "urgent", updatedAt: new Date().toISOString() };
    return delay({ ok: true, message: "Priority elevated" } as DeliveryActionResult);
  },
  async duplicate(id: string) {
    const src = store.find((j) => j.id === id);
    if (!src) return delay({ ok: false, message: "Not found" } as DeliveryActionResult);
    store = [{ ...src, id: `${src.id}-dup-${Date.now().toString(36)}`, status: "queued", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }, ...store];
    return delay({ ok: true, message: "Duplicated to queue" } as DeliveryActionResult);
  },
  async exportCsv(query: DeliveryListQuery = {}): Promise<string> {
    const items = apply(query);
    const header = "id,campaign,channel,status,total,delivered,failed,opened,clicked";
    const rows = items.map((j) =>
      [j.id, j.campaignName, j.channel, j.status, j.totalRecipients, j.delivered, j.failed, j.opened, j.clicked].join(","),
    );
    return delay([header, ...rows].join("\n"));
  },
};
