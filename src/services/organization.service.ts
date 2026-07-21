import type { Organization, OrganizationInput, OrganizationStats } from "@/types/organization";
import type { ListQuery, Paginated } from "@/types/common";
import { ORGANIZATION_TYPES, type OrganizationType } from "@/constants/rbac";
import { mockOrganizations } from "@/lib/mock/audience";
import { auditService } from "@/services/audit.service";

const NETWORK_DELAY = 260;
const delay = <T>(v: T, ms = NETWORK_DELAY) => new Promise<T>((r) => setTimeout(() => r(v), ms));

let store: Organization[] = mockOrganizations.map((o) => ({ ...o, languages: [...o.languages] }));

export interface OrganizationListQuery extends ListQuery {
  type?: OrganizationType[];
  status?: Organization["status"][];
}

function applyFilters(q: OrganizationListQuery): Organization[] {
  let items = [...store];
  if (q.search) {
    const s = q.search.toLowerCase();
    items = items.filter(
      (o) => o.name.toLowerCase().includes(s) || o.city.toLowerCase().includes(s) || o.state.toLowerCase().includes(s),
    );
  }
  if (q.type?.length) items = items.filter((o) => q.type!.includes(o.type));
  if (q.status?.length) items = items.filter((o) => q.status!.includes(o.status));
  const dir = q.sortDir === "asc" ? 1 : -1;
  const key = (q.sortBy ?? "updatedAt") as keyof Organization;
  items.sort((a, b) => {
    const av = a[key] as unknown as string | number;
    const bv = b[key] as unknown as string | number;
    if (av === bv) return 0;
    return av < bv ? -1 * dir : 1 * dir;
  });
  return items;
}

export const organizationService = {
  async list(query: OrganizationListQuery = {}): Promise<Paginated<Organization>> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 12;
    const items = applyFilters(query);
    const start = (page - 1) * pageSize;
    return delay({
      items: items.slice(start, start + pageSize),
      total: items.length,
      page,
      pageSize,
    });
  },

  async listAll(): Promise<Organization[]> {
    return delay([...store]);
  },

  async get(id: string): Promise<Organization | null> {
    return delay(store.find((o) => o.id === id) ?? null);
  },

  async getCurrent(): Promise<Organization | null> {
    return delay(store[0] ?? null);
  },

  async getStats(): Promise<OrganizationStats> {
    const total = store.length;
    const byType = new Map<string, number>();
    store.forEach((o) => byType.set(o.type, (byType.get(o.type) ?? 0) + 1));
    return delay({
      total,
      active: store.filter((o) => o.status === "active").length,
      inactive: store.filter((o) => o.status === "inactive").length,
      suspended: store.filter((o) => o.status === "suspended").length,
      byType: [...byType.entries()].map(([type, value]) => ({ type, value })),
    });
  },

  async create(input: OrganizationInput): Promise<Organization> {
    const now = new Date().toISOString();
    const org: Organization = {
      id: `org-${crypto.randomUUID().slice(0, 6)}`,
      slug: input.name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
      audienceCount: 0,
      userCount: 1,
      campaignCount: 0,
      createdAt: now,
      updatedAt: now,
      ...input,
    };
    store = [org, ...store];
    auditService.record("created", "organization", org.id, org.name);
    return delay(org);
  },

  async update(id: string, patch: Partial<OrganizationInput>): Promise<Organization> {
    const idx = store.findIndex((o) => o.id === id);
    if (idx < 0) throw new Error("Organization not found");
    const merged: Organization = { ...store[idx]!, ...patch, updatedAt: new Date().toISOString() };
    store[idx] = merged;
    auditService.record("updated", "organization", id, merged.name);
    return delay(merged);
  },

  async remove(id: string): Promise<void> {
    const org = store.find((o) => o.id === id);
    store = store.filter((o) => o.id !== id);
    if (org) auditService.record("deleted", "organization", id, org.name);
    return delay(undefined);
  },

  listTypes(): readonly OrganizationType[] {
    return ORGANIZATION_TYPES;
  },
};
