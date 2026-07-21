/**
 * Adapters translate DTOs into UI models. Each service owns its own adapter
 * so backend contract changes do not ripple into components.
 */

import type {
  UserDto,
  OrganizationDto,
  CampaignDto,
  AudienceContactDto,
  TemplateDto,
} from "../dto";

export function toUserView(u: UserDto) {
  return { id: u.id, name: u.fullName, email: u.email, avatar: u.avatarUrl, roles: u.roles, status: u.status };
}

export function toOrganizationView(o: OrganizationDto) {
  return { id: o.id, name: o.name, slug: o.slug, type: o.type, members: o.memberCount, status: o.status };
}

export function toCampaignView(c: CampaignDto) {
  return { id: c.id, name: c.name, status: c.status, channels: c.channels, audience: c.audienceCount, startsAt: c.startsAt, endsAt: c.endsAt };
}

export function toContactView(a: AudienceContactDto) {
  return { id: a.id, name: a.fullName, email: a.email, phone: a.phone, language: a.language, tags: a.tags, status: a.status };
}

export function toTemplateView(t: TemplateDto) {
  return { id: t.id, name: t.name, category: t.category, channels: t.channels, language: t.language, version: t.version, status: t.status };
}
