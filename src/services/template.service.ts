import type {
  CommunicationTemplate,
  TemplateInput,
  TemplateListQuery,
  TemplateStatus,
  TemplateVariable,
  TemplateVersion,
} from "@/types/template";
import type { Paginated } from "@/types/common";
import { mockTemplates } from "@/lib/mock/campaigns";
import { auditService } from "@/services/audit.service";
import { extractVariables } from "@/constants/template";

const NETWORK_DELAY = 220;
const delay = <T>(v: T, ms = NETWORK_DELAY) => new Promise<T>((r) => setTimeout(() => r(v), ms));

let store: CommunicationTemplate[] = mockTemplates.map((t) => ({
  ...t,
  variables: [...t.variables],
  versions: t.versions.map((v) => ({ ...v })),
}));

function clone(t: CommunicationTemplate): CommunicationTemplate {
  return { ...t, variables: [...t.variables], versions: t.versions.map((v) => ({ ...v })) };
}

function synthesizeVariables(body: string, extra: TemplateVariable[] = []): TemplateVariable[] {
  const keys = extractVariables(body);
  const map = new Map<string, TemplateVariable>();
  keys.forEach((k) => map.set(k, { key: k, label: k.replace(/_/g, " ") }));
  extra.forEach((v) => map.set(v.key, v));
  return [...map.values()];
}

function applyFilters(q: TemplateListQuery): CommunicationTemplate[] {
  let items = store.filter((t) => !t.archivedAt || q.status?.includes("archived"));
  if (q.search) {
    const s = q.search.toLowerCase();
    items = items.filter(
      (t) => t.name.toLowerCase().includes(s) || t.body.toLowerCase().includes(s) || (t.subject ?? "").toLowerCase().includes(s),
    );
  }
  if (q.category?.length) items = items.filter((t) => q.category!.includes(t.category));
  if (q.language?.length) items = items.filter((t) => q.language!.includes(t.language));
  if (q.status?.length) items = items.filter((t) => q.status!.includes(t.status));
  if (q.createdBy) items = items.filter((t) => t.createdBy === q.createdBy);

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

export const templateService = {
  async list(query: TemplateListQuery = {}): Promise<Paginated<CommunicationTemplate>> {
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

  async listAll(query: TemplateListQuery = {}): Promise<CommunicationTemplate[]> {
    return delay(applyFilters(query).map(clone));
  },

  async get(id: string): Promise<CommunicationTemplate | null> {
    const t = store.find((x) => x.id === id);
    return delay(t ? clone(t) : null);
  },

  async create(input: TemplateInput, author = { id: "user-1", name: "You" }): Promise<CommunicationTemplate> {
    const now = new Date().toISOString();
    const version: TemplateVersion = {
      id: `ver-${crypto.randomUUID?.().slice(0, 6) ?? Math.random().toString(36).slice(2, 8)}`,
      version: 1,
      subject: input.subject,
      body: input.body,
      authorId: author.id,
      authorName: author.name,
      note: input.versionNote ?? "Initial version",
      createdAt: now,
    };
    const t: CommunicationTemplate = {
      id: `tpl-${crypto.randomUUID?.().slice(0, 8) ?? Math.random().toString(36).slice(2, 10)}`,
      name: input.name,
      category: input.category,
      language: input.language,
      status: input.status ?? "draft",
      subject: input.subject,
      body: input.body,
      variables: synthesizeVariables(input.body, input.variables),
      version: 1,
      versions: [version],
      usageCount: 0,
      createdBy: author.id,
      createdByName: author.name,
      createdAt: now,
      updatedAt: now,
    };
    store = [t, ...store];
    auditService.record("created", "campaign", t.id, t.name);
    return delay(clone(t));
  },

  async update(id: string, patch: Partial<TemplateInput>, author = { id: "user-1", name: "You" }): Promise<CommunicationTemplate> {
    const idx = store.findIndex((t) => t.id === id);
    if (idx < 0) throw new Error("Template not found");
    const existing = store[idx]!;
    const bodyChanged = patch.body != null && patch.body !== existing.body;
    const subjectChanged = patch.subject != null && patch.subject !== existing.subject;
    const now = new Date().toISOString();

    const updated: CommunicationTemplate = {
      ...existing,
      ...patch,
      subject: patch.subject ?? existing.subject,
      body: patch.body ?? existing.body,
      variables: synthesizeVariables(patch.body ?? existing.body, patch.variables ?? existing.variables),
      updatedAt: now,
    };

    if (bodyChanged || subjectChanged) {
      const version = existing.version + 1;
      const ver: TemplateVersion = {
        id: `ver-${crypto.randomUUID?.().slice(0, 6) ?? Math.random().toString(36).slice(2, 8)}`,
        version,
        subject: updated.subject,
        body: updated.body,
        authorId: author.id,
        authorName: author.name,
        note: patch.versionNote,
        createdAt: now,
      };
      updated.version = version;
      updated.versions = [ver, ...existing.versions];
    }

    store[idx] = updated;
    auditService.record("updated", "campaign", updated.id, updated.name);
    return delay(clone(updated));
  },

  async duplicate(id: string): Promise<CommunicationTemplate> {
    const t = store.find((x) => x.id === id);
    if (!t) throw new Error("Template not found");
    const now = new Date().toISOString();
    const copy: CommunicationTemplate = {
      ...clone(t),
      id: `tpl-${crypto.randomUUID?.().slice(0, 8) ?? Math.random().toString(36).slice(2, 10)}`,
      name: `${t.name} (Copy)`,
      status: "draft",
      usageCount: 0,
      version: 1,
      versions: [{ ...t.versions[0]!, id: `ver-${Math.random().toString(36).slice(2, 8)}`, version: 1, note: "Duplicated", createdAt: now }],
      createdAt: now,
      updatedAt: now,
    };
    store = [copy, ...store];
    return delay(clone(copy));
  },

  async setStatus(id: string, status: TemplateStatus): Promise<void> {
    const idx = store.findIndex((t) => t.id === id);
    if (idx < 0) return;
    store[idx] = { ...store[idx]!, status, updatedAt: new Date().toISOString(), archivedAt: status === "archived" ? new Date().toISOString() : undefined };
    auditService.record("updated", "campaign", id, undefined, { status });
    return delay(undefined);
  },

  async restoreVersion(id: string, versionId: string, author = { id: "user-1", name: "You" }): Promise<CommunicationTemplate> {
    const idx = store.findIndex((t) => t.id === id);
    if (idx < 0) throw new Error("Template not found");
    const existing = store[idx]!;
    const target = existing.versions.find((v) => v.id === versionId);
    if (!target) throw new Error("Version not found");
    return this.update(id, { subject: target.subject, body: target.body, versionNote: `Restored v${target.version}` }, author);
  },

  async remove(id: string): Promise<void> {
    store = store.filter((t) => t.id !== id);
    auditService.record("deleted", "campaign", id);
    return delay(undefined);
  },
};
