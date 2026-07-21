import type {
  AudienceActivityEvent,
  AudienceContact,
  AudienceInput,
  AudienceListQuery,
  AudienceStats,
  AudienceStatus,
} from "@/types/audience";
import type { Paginated } from "@/types/common";
import { mockAudience, mockAudienceTags } from "@/lib/mock/audience";
import { auditService } from "@/services/audit.service";

/**
 * Audience service.
 *
 * Backed by centralized mock data. Every call returns the shape the future
 * FastAPI backend will produce, so the UI stays untouched at cutover.
 */

const NETWORK_DELAY = 260;
const delay = <T>(v: T, ms = NETWORK_DELAY) => new Promise<T>((r) => setTimeout(() => r(v), ms));

// In-memory store — clones so consumers can't mutate the fixture.
let store: AudienceContact[] = mockAudience.map((c) => ({ ...c, tags: [...c.tags], groupIds: [...c.groupIds] }));

function clone(c: AudienceContact): AudienceContact {
  return { ...c, tags: c.tags.map((t) => ({ ...t })), groupIds: [...c.groupIds] };
}

function applyFilters(query: AudienceListQuery): AudienceContact[] {
  const {
    search,
    status,
    states,
    languages,
    channels,
    tagIds,
    groupIds,
    sortBy = "updatedAt",
    sortDir = "desc",
  } = query;

  let items = store.filter((c) => !c.deletedAt);

  if (search) {
    const q = search.toLowerCase();
    items = items.filter(
      (c) =>
        c.fullName.toLowerCase().includes(q) ||
        c.email.toLowerCase().includes(q) ||
        c.phone.toLowerCase().includes(q) ||
        c.city.toLowerCase().includes(q),
    );
  }
  if (status?.length) items = items.filter((c) => status.includes(c.status));
  if (states?.length) items = items.filter((c) => states.includes(c.state));
  if (languages?.length) items = items.filter((c) => languages.includes(c.preferredLanguage));
  if (channels?.length) items = items.filter((c) => channels.includes(c.preferredChannel));
  if (tagIds?.length) items = items.filter((c) => c.tags.some((t) => tagIds.includes(t.id)));
  if (groupIds?.length) items = items.filter((c) => c.groupIds.some((g) => groupIds.includes(g)));

  const dir = sortDir === "asc" ? 1 : -1;
  items = [...items].sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[sortBy as string];
    const bv = (b as unknown as Record<string, unknown>)[sortBy as string];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });

  return items;
}

function computeStats(): AudienceStats {
  const items = store.filter((c) => !c.deletedAt);
  const total = items.length;
  const active = items.filter((c) => c.status === "active").length;
  const inactive = items.filter((c) => c.status === "inactive").length;
  const now = Date.now();
  const recentlyAdded = items.filter(
    (c) => now - new Date(c.createdAt).getTime() < 1000 * 60 * 60 * 24 * 14,
  ).length;

  const tally = <K extends string>(key: (c: AudienceContact) => K) => {
    const m = new Map<string, number>();
    items.forEach((c) => {
      const k = key(c);
      m.set(k, (m.get(k) ?? 0) + 1);
    });
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  };

  return {
    total,
    active,
    inactive,
    recentlyAdded,
    languageDistribution: tally((c) => c.preferredLanguage).map(([language, value]) => ({ language, value })),
    stateDistribution: tally((c) => c.state).map(([state, value]) => ({ state, value })),
    channelDistribution: tally((c) => c.preferredChannel).map(([channel, value]) => ({ channel, value })),
  };
}

export const audienceService = {
  async list(query: AudienceListQuery = {}): Promise<Paginated<AudienceContact>> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 25;
    const items = applyFilters(query);
    const start = (page - 1) * pageSize;
    return delay({
      items: items.slice(start, start + pageSize).map(clone),
      total: items.length,
      page,
      pageSize,
    });
  },

  async listAll(query: AudienceListQuery = {}): Promise<AudienceContact[]> {
    return delay(applyFilters(query).map(clone));
  },

  async get(id: string): Promise<AudienceContact | null> {
    const found = store.find((c) => c.id === id && !c.deletedAt);
    return delay(found ? clone(found) : null);
  },

  async getStats(): Promise<AudienceStats> {
    return delay(computeStats());
  },

  async create(input: AudienceInput): Promise<AudienceContact> {
    const now = new Date().toISOString();
    const tags = (input.tagIds ?? []).map((id) => {
      const t = mockAudienceTags.find((x) => x.id === id);
      return t ? { id: t.id, name: t.name, color: t.color } : { id, name: id, color: "#94A3B8" };
    });
    const contact: AudienceContact = {
      id: `aud-${crypto.randomUUID().slice(0, 8)}`,
      firstName: input.firstName,
      lastName: input.lastName,
      fullName: `${input.firstName} ${input.lastName}`,
      email: input.email,
      phone: input.phone,
      alternatePhone: input.alternatePhone,
      dateOfBirth: input.dateOfBirth,
      gender: input.gender,
      occupation: input.occupation,
      organizationId: input.organizationId,
      organizationName: undefined,
      department: input.department,
      state: input.state,
      district: input.district,
      city: input.city,
      address: input.address,
      pincode: input.pincode,
      preferredLanguage: input.preferredLanguage,
      preferredChannel: input.preferredChannel,
      tags,
      groupIds: input.groupIds ?? [],
      status: input.status,
      notes: input.notes,
      avatarUrl: input.avatarUrl,
      consentGiven: input.consentGiven,
      createdAt: now,
      updatedAt: now,
      deletedAt: null,
    };
    store = [contact, ...store];
    auditService.record("created", "audience", contact.id, contact.fullName);
    return delay(clone(contact));
  },

  async update(id: string, patch: Partial<AudienceInput>): Promise<AudienceContact> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) throw new Error("Audience not found");
    const existing = store[idx]!;
    const merged: AudienceContact = {
      ...existing,
      ...patch,
      firstName: patch.firstName ?? existing.firstName,
      lastName: patch.lastName ?? existing.lastName,
      fullName: `${patch.firstName ?? existing.firstName} ${patch.lastName ?? existing.lastName}`,
      tags: patch.tagIds
        ? patch.tagIds.map((tid) => {
            const t = mockAudienceTags.find((x) => x.id === tid);
            return t ? { id: t.id, name: t.name, color: t.color } : { id: tid, name: tid, color: "#94A3B8" };
          })
        : existing.tags,
      groupIds: patch.groupIds ?? existing.groupIds,
      updatedAt: new Date().toISOString(),
    };
    store[idx] = merged;
    auditService.record("updated", "audience", merged.id, merged.fullName);
    return delay(clone(merged));
  },

  async remove(id: string): Promise<void> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) return;
    store[idx] = { ...store[idx]!, deletedAt: new Date().toISOString() };
    auditService.record("deleted", "audience", id, store[idx]!.fullName);
    return delay(undefined);
  },

  async restore(id: string): Promise<void> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) return;
    store[idx] = { ...store[idx]!, deletedAt: null };
    auditService.record("updated", "audience", id, store[idx]!.fullName, { restored: true });
    return delay(undefined);
  },

  async bulkRemove(ids: string[]): Promise<void> {
    const set = new Set(ids);
    const stamp = new Date().toISOString();
    store = store.map((c) => (set.has(c.id) ? { ...c, deletedAt: stamp } : c));
    ids.forEach((id) => auditService.record("deleted", "audience", id));
    return delay(undefined);
  },

  async bulkUpdateStatus(ids: string[], status: AudienceStatus): Promise<void> {
    const set = new Set(ids);
    const stamp = new Date().toISOString();
    store = store.map((c) => (set.has(c.id) ? { ...c, status, updatedAt: stamp } : c));
    ids.forEach((id) => auditService.record("updated", "audience", id, undefined, { status }));
    return delay(undefined);
  },

  async bulkAssignTags(ids: string[], tagIds: string[]): Promise<void> {
    const set = new Set(ids);
    const stamp = new Date().toISOString();
    const tags = tagIds.map((tid) => {
      const t = mockAudienceTags.find((x) => x.id === tid);
      return t ? { id: t.id, name: t.name, color: t.color } : { id: tid, name: tid, color: "#94A3B8" };
    });
    store = store.map((c) => {
      if (!set.has(c.id)) return c;
      const existingIds = new Set(c.tags.map((t) => t.id));
      const merged = [...c.tags, ...tags.filter((t) => !existingIds.has(t.id))];
      return { ...c, tags: merged, updatedAt: stamp };
    });
    ids.forEach((id) => auditService.record("assigned", "audience_tag", id));
    return delay(undefined);
  },

  async activity(id: string): Promise<AudienceActivityEvent[]> {
    const contact = store.find((c) => c.id === id);
    if (!contact) return delay([]);
    const now = Date.now();
    const events: AudienceActivityEvent[] = [
      { id: "e1", type: "created", message: "Contact record created", actor: "System", at: contact.createdAt },
      { id: "e2", type: "consent", message: contact.consentGiven ? "Consent granted for communication" : "Consent pending", actor: "Contact", at: contact.createdAt },
      { id: "e3", type: "campaign_delivered", message: "Vaccination Drive — Phase 2 delivered via SMS", actor: "System", at: new Date(now - 1000 * 60 * 60 * 24 * 3).toISOString() },
      { id: "e4", type: "campaign_opened", message: "Opened Monsoon Health Advisory", actor: "Contact", at: new Date(now - 1000 * 60 * 60 * 24 * 2).toISOString() },
      { id: "e5", type: "updated", message: "Preferred language updated", actor: "Ananya Iyer", at: contact.updatedAt },
    ];
    return delay(events);
  },
};
