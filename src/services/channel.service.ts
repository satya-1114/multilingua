import type { Channel, ChannelTestInput, ChannelTestResult } from "@/types/channel";
import { mockChannels } from "@/lib/mock/communication";

const delay = <T>(v: T, ms = 200): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let store: Channel[] = mockChannels.map((c) => ({ ...c }));

export const channelService = {
  async list(): Promise<Channel[]> { return delay([...store]); },
  async get(id: string): Promise<Channel | null> { return delay(store.find((c) => c.id === id) ?? null); },
  async update(id: string, patch: Partial<Channel>): Promise<Channel | null> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) return delay(null);
    store[idx] = { ...store[idx]!, ...patch, updatedAt: new Date().toISOString() };
    return delay(store[idx]!);
  },
  async setStatus(id: string, status: Channel["status"]): Promise<Channel | null> {
    return channelService.update(id, { status });
  },
  async test(input: ChannelTestInput): Promise<ChannelTestResult> {
    const c = store.find((x) => x.id === input.channelId);
    if (!c || c.status === "offline" || c.status === "planned") {
      return delay({ ok: false, latencyMs: 0, error: "Channel unavailable" });
    }
    return delay({
      ok: true,
      latencyMs: Math.round(80 + Math.random() * 260),
      providerMessageId: `msg_${Date.now().toString(36)}`,
    }, 500);
  },
};
