/**
 * In-memory cache with namespaced buckets, TTL, and workspace scoping.
 */

interface Entry<T> { value: T; expiresAt: number }

class CacheService {
  private buckets = new Map<string, Map<string, Entry<unknown>>>();

  private bucket(name: string): Map<string, Entry<unknown>> {
    let b = this.buckets.get(name);
    if (!b) { b = new Map(); this.buckets.set(name, b); }
    return b;
  }

  set<T>(bucket: string, key: string, value: T, ttlMs = 60_000) {
    this.bucket(bucket).set(key, { value, expiresAt: Date.now() + ttlMs });
  }

  get<T>(bucket: string, key: string): T | null {
    const entry = this.bucket(bucket).get(key) as Entry<T> | undefined;
    if (!entry) return null;
    if (entry.expiresAt < Date.now()) { this.bucket(bucket).delete(key); return null; }
    return entry.value;
  }

  invalidate(bucket: string, key?: string) {
    if (!key) this.bucket(bucket).clear();
    else this.bucket(bucket).delete(key);
  }

  invalidateAll() { this.buckets.clear(); }

  stats() {
    const out: Record<string, number> = {};
    for (const [k, v] of this.buckets) out[k] = v.size;
    return out;
  }
}

export const cacheService = new CacheService();

export const CacheBuckets = {
  entity: "entity",
  request: "request",
  workspace: "workspace",
  permission: "permission",
  search: "search",
} as const;
