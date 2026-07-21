import type {
  Campaign,
  CampaignActivityEntry,
  CampaignInput,
  CampaignListQuery,
  CampaignNote,
  CampaignStats,
  CampaignStatus,
} from "@/types/campaign";
import type { Paginated } from "@/types/common";
import { mockCampaigns } from "@/lib/mock/campaigns";
import { auditService } from "@/services/audit.service";
import { CAMPAIGN_STATUS_META, CAMPAIGN_TYPES, isTransitionAllowed } from "@/constants/campaign";
import { workflowService } from "@/services/workflow.service";

const NETWORK_DELAY = 240;
const delay = <T>(v: T, ms = NETWORK_DELAY) => new Promise<T>((r) => setTimeout(() => r(v), ms));

let store: Campaign[] = mockCampaigns.map((c) => ({
  ...c,
  tags: [...c.tags],
  audienceGroupIds: [...c.audienceGroupIds],
  audienceContactIds: [...c.audienceContactIds],
  languages: [...c.languages],
  approvals: c.approvals.map((a) => ({ ...a })),
  activity: c.activity.map((a) => ({ ...a })),
  notes: c.notes.map((n) => ({ ...n })),
  schedule: { ...c.schedule },
}));

function clone(c: Campaign): Campaign {
  return {
    ...c,
    tags: [...c.tags],
    audienceGroupIds: [...c.audienceGroupIds],
    audienceContactIds: [...c.audienceContactIds],
    languages: [...c.languages],
    approvals: c.approvals.map((a) => ({ ...a })),
    activity: c.activity.map((a) => ({ ...a })),
    notes: c.notes.map((n) => ({ ...n })),
    schedule: { ...c.schedule },
  };
}

function nextCode(): string {
  const year = new Date().getFullYear();
  const n = store.length + 1;
  return `CMP-${year}-${n.toString().padStart(4, "0")}`;
}

function applyFilters(q: CampaignListQuery): Campaign[] {
  let items = [...store];
  if (q.search) {
    const s = q.search.toLowerCase();
    items = items.filter(
      (c) =>
        c.name.toLowerCase().includes(s) ||
        c.code.toLowerCase().includes(s) ||
        c.description?.toLowerCase().includes(s) ||
        c.tags.some((t) => t.toLowerCase().includes(s)),
    );
  }
  if (q.status?.length) items = items.filter((c) => q.status!.includes(c.status));
  if (q.type?.length) items = items.filter((c) => q.type!.includes(c.type));
  if (q.priority?.length) items = items.filter((c) => q.priority!.includes(c.priority));
  if (q.category?.length) items = items.filter((c) => q.category!.includes(c.category));
  if (q.ownerId) items = items.filter((c) => c.ownerId === q.ownerId);
  if (q.organizationId) items = items.filter((c) => c.organizationId === q.organizationId);
  if (q.from) items = items.filter((c) => (c.schedule.startAt ?? c.createdAt) >= q.from!);
  if (q.to) items = items.filter((c) => (c.schedule.startAt ?? c.createdAt) <= q.to!);

  const sortBy = q.sortBy ?? "updatedAt";
  const dir = q.sortDir === "asc" ? 1 : -1;
  items.sort((a, b) => {
    const av = (a as unknown as Record<string, unknown>)[sortBy];
    const bv = (b as unknown as Record<string, unknown>)[sortBy];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });
  return items;
}

function pushActivity(c: Campaign, entry: Omit<CampaignActivityEntry, "id" | "at">) {
  c.activity = [
    {
      id: `evt-${crypto.randomUUID?.().slice(0, 6) ?? Math.random().toString(36).slice(2, 8)}`,
      at: new Date().toISOString(),
      ...entry,
    },
    ...c.activity,
  ];
}

export const campaignService = {
  async list(query: CampaignListQuery = {}): Promise<Paginated<Campaign>> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 20;
    const items = applyFilters(query);
    const start = (page - 1) * pageSize;
    return delay({
      items: items.slice(start, start + pageSize).map(clone),
      total: items.length,
      page,
      pageSize,
    });
  },

  async listAll(query: CampaignListQuery = {}): Promise<Campaign[]> {
    return delay(applyFilters(query).map(clone));
  },

  async get(id: string): Promise<Campaign | null> {
    const c = store.find((x) => x.id === id);
    return delay(c ? clone(c) : null);
  },

  async getStats(): Promise<CampaignStats> {
    const items = store;
    const bucket = (key: CampaignStatus) => items.filter((c) => c.status === key).length;
    const now = new Date();
    const monthly: { month: string; count: number }[] = [];
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const label = d.toLocaleString("en", { month: "short" });
      const count = items.filter((c) => {
        const cd = new Date(c.createdAt);
        return cd.getMonth() === d.getMonth() && cd.getFullYear() === d.getFullYear();
      }).length;
      monthly.push({ month: label, count });
    }
    const byType = CAMPAIGN_TYPES.map((t) => ({
      type: t.key,
      value: items.filter((c) => c.type === t.key).length,
    })).filter((r) => r.value > 0);
    const performance = items
      .filter((c) => ["running", "completed", "archived"].includes(c.status))
      .slice(0, 6)
      .map((c) => {
        const delivered = Math.round(c.estimatedReach * (0.72 + Math.random() * 0.2));
        const opened = Math.round(delivered * (0.35 + Math.random() * 0.25));
        const failed = Math.round(c.estimatedReach * (Math.random() * 0.05));
        return { name: c.name.length > 22 ? c.name.slice(0, 22) + "…" : c.name, delivered, opened, failed };
      });
    const trend: { day: string; delivered: number }[] = Array.from({ length: 14 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (13 - i));
      return { day: d.toLocaleDateString("en", { day: "2-digit", month: "short" }), delivered: 1200 + Math.floor(Math.random() * 900) };
    });
    return delay({
      total: items.length,
      draft: bucket("draft"),
      scheduled: bucket("scheduled"),
      running: bucket("running"),
      completed: bucket("completed"),
      archived: bucket("archived"),
      failed: bucket("failed"),
      cancelled: bucket("cancelled"),
      pendingApproval: bucket("pending_approval"),
      monthly,
      byType,
      performance,
      trend,
    });
  },

  async create(input: CampaignInput, ownerName = "You"): Promise<Campaign> {
    const now = new Date().toISOString();
    const c: Campaign = {
      id: `cmp-${crypto.randomUUID?.().slice(0, 8) ?? Math.random().toString(36).slice(2, 10)}`,
      code: nextCode(),
      name: input.name,
      description: input.description,
      objective: input.objective,
      type: input.type,
      category: input.category,
      priority: input.priority,
      visibility: input.visibility,
      status: input.schedule.mode === "publish_now" ? "running" : "draft",
      color: input.color,
      icon: input.icon,
      tags: input.tags,
      organizationId: input.organizationId,
      organizationName: input.organizationId,
      department: input.department,
      ownerId: input.ownerId,
      ownerName,
      audienceGroupIds: input.audienceGroupIds,
      audienceContactIds: input.audienceContactIds,
      estimatedReach: 0,
      languages: input.languages,
      templateId: input.templateId,
      schedule: input.schedule,
      approvals: [],
      activity: [
        {
          id: "evt-0",
          type: "created",
          message: "Campaign created",
          actor: ownerName,
          at: now,
        },
      ],
      notes: [],
      createdAt: now,
      updatedAt: now,
    };
    store = [c, ...store];
    auditService.record("created", "campaign", c.id, c.name);
    return delay(clone(c));
  },

  async update(id: string, patch: Partial<CampaignInput>): Promise<Campaign> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) throw new Error("Campaign not found");
    const existing = store[idx]!;
    const merged: Campaign = {
      ...existing,
      ...patch,
      tags: patch.tags ?? existing.tags,
      audienceGroupIds: patch.audienceGroupIds ?? existing.audienceGroupIds,
      audienceContactIds: patch.audienceContactIds ?? existing.audienceContactIds,
      languages: patch.languages ?? existing.languages,
      schedule: patch.schedule ? { ...existing.schedule, ...patch.schedule } : existing.schedule,
      updatedAt: new Date().toISOString(),
    };
    pushActivity(merged, { type: "updated", message: "Campaign updated", actor: merged.ownerName });
    store[idx] = merged;
    auditService.record("updated", "campaign", merged.id, merged.name);
    return delay(clone(merged));
  },

  async setStatus(id: string, next: CampaignStatus, actor = "You", note?: string): Promise<Campaign> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) throw new Error("Campaign not found");
    const current = store[idx]!;
    if (!isTransitionAllowed(current.status, next)) {
      throw new Error(
        `Cannot transition from ${CAMPAIGN_STATUS_META[current.status].label} to ${CAMPAIGN_STATUS_META[next].label}.`,
      );
    }
    const updated: Campaign = { ...current, status: next, updatedAt: new Date().toISOString() };
    if (next === "running") updated.launchedAt = updated.updatedAt;
    if (next === "completed") updated.completedAt = updated.updatedAt;
    if (next === "archived") updated.archivedAt = updated.updatedAt;
    pushActivity(updated, {
      type: "status_changed",
      message: `Status changed to ${CAMPAIGN_STATUS_META[next].label}${note ? ` — ${note}` : ""}`,
      actor,
    });
    store[idx] = updated;
    workflowService.recordTransition(id, current.status, next, actor, note);
    auditService.record("updated", "campaign", id, updated.name, { status: next });
    return delay(clone(updated));
  },

  async duplicate(id: string): Promise<Campaign> {
    const c = store.find((x) => x.id === id);
    if (!c) throw new Error("Campaign not found");
    const now = new Date().toISOString();
    const copy: Campaign = {
      ...clone(c),
      id: `cmp-${crypto.randomUUID?.().slice(0, 8) ?? Math.random().toString(36).slice(2, 10)}`,
      code: nextCode(),
      name: `${c.name} (Copy)`,
      status: "draft",
      approvals: [],
      activity: [
        { id: "evt-0", type: "duplicated", message: `Duplicated from ${c.code}`, actor: c.ownerName, at: now },
      ],
      createdAt: now,
      updatedAt: now,
      launchedAt: undefined,
      completedAt: undefined,
      archivedAt: undefined,
    };
    store = [copy, ...store];
    auditService.record("created", "campaign", copy.id, copy.name, { duplicatedFrom: c.id });
    return delay(clone(copy));
  },

  async remove(id: string): Promise<void> {
    store = store.filter((c) => c.id !== id);
    auditService.record("deleted", "campaign", id);
    return delay(undefined);
  },

  async bulkStatus(ids: string[], status: CampaignStatus, actor = "You"): Promise<void> {
    for (const id of ids) {
      try {
        await this.setStatus(id, status, actor);
      } catch {
        // skip invalid transitions silently in bulk
      }
    }
  },

  async bulkArchive(ids: string[], actor = "You"): Promise<void> {
    for (const id of ids) {
      const c = store.find((x) => x.id === id);
      if (!c) continue;
      if (isTransitionAllowed(c.status, "archived")) {
        await this.setStatus(id, "archived", actor);
      } else {
        // force archive
        const idx = store.findIndex((x) => x.id === id);
        const updated = { ...c, status: "archived" as CampaignStatus, archivedAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
        pushActivity(updated, { type: "archived", message: "Archived (bulk)", actor });
        store[idx] = updated;
        auditService.record("updated", "campaign", id, c.name, { status: "archived" });
      }
    }
  },

  async bulkDelete(ids: string[]): Promise<void> {
    const set = new Set(ids);
    store = store.filter((c) => !set.has(c.id));
    ids.forEach((id) => auditService.record("deleted", "campaign", id));
    return delay(undefined);
  },

  async bulkDuplicate(ids: string[]): Promise<Campaign[]> {
    const out: Campaign[] = [];
    for (const id of ids) out.push(await this.duplicate(id));
    return out;
  },

  async addNote(id: string, body: string, authorId: string, authorName: string, pinned = false): Promise<CampaignNote> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) throw new Error("Campaign not found");
    const note: CampaignNote = {
      id: `note-${crypto.randomUUID?.().slice(0, 6) ?? Math.random().toString(36).slice(2, 8)}`,
      body,
      authorId,
      authorName,
      pinned,
      createdAt: new Date().toISOString(),
    };
    const updated = { ...store[idx]!, notes: [note, ...store[idx]!.notes] };
    pushActivity(updated, { type: "note", message: "Added a note", actor: authorName });
    store[idx] = updated;
    return delay(note);
  },

  async togglePinNote(id: string, noteId: string): Promise<void> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) return;
    const updated = {
      ...store[idx]!,
      notes: store[idx]!.notes.map((n) => (n.id === noteId ? { ...n, pinned: !n.pinned } : n)),
    };
    store[idx] = updated;
    return delay(undefined);
  },

  async pushApproval(
    id: string,
    entry: Omit<import("@/types/campaign").CampaignApprovalEntry, "id" | "at">,
  ): Promise<Campaign> {
    const idx = store.findIndex((c) => c.id === id);
    if (idx < 0) throw new Error("Campaign not found");
    const updated: Campaign = {
      ...store[idx]!,
      approvals: [
        ...store[idx]!.approvals,
        {
          id: `apr-${crypto.randomUUID?.().slice(0, 6) ?? Math.random().toString(36).slice(2, 8)}`,
          at: new Date().toISOString(),
          ...entry,
        },
      ],
      updatedAt: new Date().toISOString(),
    };
    pushActivity(updated, {
      type: entry.status === "approved" ? "approved" : entry.status === "rejected" ? "rejected" : entry.status === "sent_back" ? "sent_back" : "submitted",
      message:
        entry.status === "approved" ? "Approved" :
        entry.status === "rejected" ? "Rejected" :
        entry.status === "sent_back" ? "Sent back for changes" : "Submitted for approval",
      actor: entry.actorName,
    });
    store[idx] = updated;
    return delay(clone(updated));
  },
};
