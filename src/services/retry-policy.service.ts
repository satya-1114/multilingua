import type { RetryPolicy, RetryPolicyInput } from "@/types/retry-policy";
import { mockRetryPolicies } from "@/lib/mock/communication";

const delay = <T>(v: T, ms = 180): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let store: RetryPolicy[] = [...mockRetryPolicies];

export const retryPolicyService = {
  async list(): Promise<RetryPolicy[]> { return delay([...store]); },
  async get(id: string): Promise<RetryPolicy | null> { return delay(store.find((p) => p.id === id) ?? null); },
  async create(input: RetryPolicyInput): Promise<RetryPolicy> {
    const now = new Date().toISOString();
    const rec: RetryPolicy = { id: `rp-${Date.now().toString(36)}`, isDefault: false, createdAt: now, updatedAt: now, ...input };
    store = [rec, ...store];
    return delay(rec);
  },
  async update(id: string, patch: Partial<RetryPolicyInput>): Promise<RetryPolicy | null> {
    const idx = store.findIndex((p) => p.id === id);
    if (idx < 0) return delay(null);
    store[idx] = { ...store[idx]!, ...patch, updatedAt: new Date().toISOString() };
    return delay(store[idx]!);
  },
  async remove(id: string) {
    store = store.filter((p) => p.id !== id);
    return delay({ ok: true });
  },
  simulateNextAttempts(policy: RetryPolicy): Array<{ attempt: number; delaySec: number }> {
    const out: Array<{ attempt: number; delaySec: number }> = [];
    let d = policy.intervalSeconds;
    for (let i = 1; i <= policy.maxAttempts; i++) {
      out.push({ attempt: i, delaySec: Math.min(d, policy.maxIntervalSeconds) });
      if (policy.backoff === "exponential") d = Math.round(d * policy.backoffMultiplier);
      else if (policy.backoff === "linear") d = Math.round(d + policy.intervalSeconds * (policy.backoffMultiplier - 1 + 1));
    }
    return out;
  },
};
