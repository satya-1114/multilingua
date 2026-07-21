import type { AudienceGroup, AudienceTag } from "@/types/audience";
import { mockAudienceGroups, mockAudienceTags } from "@/lib/mock/audience";
import { auditService } from "@/services/audit.service";

const delay = <T>(v: T, ms = 200) => new Promise<T>((r) => setTimeout(() => r(v), ms));

let tags: AudienceTag[] = [...mockAudienceTags];
let groups: AudienceGroup[] = [...mockAudienceGroups];

export const tagService = {
  async list(): Promise<AudienceTag[]> {
    return delay([...tags]);
  },
  async create(input: { name: string; color: string }): Promise<AudienceTag> {
    const tag: AudienceTag = {
      id: `tag-${crypto.randomUUID().slice(0, 6)}`,
      name: input.name.trim(),
      color: input.color,
      audienceCount: 0,
      createdAt: new Date().toISOString(),
    };
    tags = [tag, ...tags];
    auditService.record("created", "audience_tag", tag.id, tag.name);
    return delay(tag);
  },
  async update(id: string, patch: Partial<Pick<AudienceTag, "name" | "color">>): Promise<AudienceTag> {
    const idx = tags.findIndex((t) => t.id === id);
    if (idx < 0) throw new Error("Tag not found");
    tags[idx] = { ...tags[idx]!, ...patch };
    auditService.record("updated", "audience_tag", id, tags[idx]!.name);
    return delay(tags[idx]!);
  },
  async remove(id: string): Promise<void> {
    const tag = tags.find((t) => t.id === id);
    tags = tags.filter((t) => t.id !== id);
    if (tag) auditService.record("deleted", "audience_tag", id, tag.name);
    return delay(undefined);
  },
  async merge(sourceIds: string[], targetId: string): Promise<AudienceTag> {
    const target = tags.find((t) => t.id === targetId);
    if (!target) throw new Error("Target tag not found");
    const mergedCount = sourceIds.reduce((sum, sid) => {
      const s = tags.find((t) => t.id === sid);
      return sum + (s?.audienceCount ?? 0);
    }, target.audienceCount);
    tags = tags.filter((t) => t.id === targetId || !sourceIds.includes(t.id));
    const idx = tags.findIndex((t) => t.id === targetId);
    tags[idx] = { ...tags[idx]!, audienceCount: mergedCount };
    auditService.record("updated", "audience_tag", targetId, target.name, { mergedFrom: sourceIds });
    return delay(tags[idx]!);
  },
};

export const groupService = {
  async list(): Promise<AudienceGroup[]> {
    return delay([...groups]);
  },
  async get(id: string): Promise<AudienceGroup | null> {
    return delay(groups.find((g) => g.id === id) ?? null);
  },
  async create(input: { name: string; description?: string; color: string }): Promise<AudienceGroup> {
    const now = new Date().toISOString();
    const g: AudienceGroup = {
      id: `grp-${crypto.randomUUID().slice(0, 6)}`,
      name: input.name.trim(),
      description: input.description,
      color: input.color,
      memberCount: 0,
      createdAt: now,
      updatedAt: now,
    };
    groups = [g, ...groups];
    auditService.record("created", "audience_group", g.id, g.name);
    return delay(g);
  },
  async update(id: string, patch: Partial<Pick<AudienceGroup, "name" | "description" | "color">>): Promise<AudienceGroup> {
    const idx = groups.findIndex((g) => g.id === id);
    if (idx < 0) throw new Error("Group not found");
    groups[idx] = { ...groups[idx]!, ...patch, updatedAt: new Date().toISOString() };
    auditService.record("updated", "audience_group", id, groups[idx]!.name);
    return delay(groups[idx]!);
  },
  async remove(id: string): Promise<void> {
    const g = groups.find((x) => x.id === id);
    groups = groups.filter((x) => x.id !== id);
    if (g) auditService.record("deleted", "audience_group", id, g.name);
    return delay(undefined);
  },
  async assignMembers(groupId: string, count: number): Promise<AudienceGroup> {
    const idx = groups.findIndex((g) => g.id === groupId);
    if (idx < 0) throw new Error("Group not found");
    groups[idx] = { ...groups[idx]!, memberCount: groups[idx]!.memberCount + count };
    auditService.record("assigned", "audience_group", groupId, groups[idx]!.name, { count });
    return delay(groups[idx]!);
  },
  async removeMembers(groupId: string, count: number): Promise<AudienceGroup> {
    const idx = groups.findIndex((g) => g.id === groupId);
    if (idx < 0) throw new Error("Group not found");
    groups[idx] = { ...groups[idx]!, memberCount: Math.max(0, groups[idx]!.memberCount - count) };
    auditService.record("unassigned", "audience_group", groupId, groups[idx]!.name, { count });
    return delay(groups[idx]!);
  },
};
