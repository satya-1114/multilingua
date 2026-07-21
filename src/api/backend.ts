/**
 * Real-backend adapters for the CRUD backbone (Users, Organizations,
 * Workspaces, Audience, Campaigns, Templates).
 *
 * These call the FastAPI backend directly through `apiService`. They are
 * intentionally decoupled from the rich mock services in `src/services/*`
 * so consumers can migrate one call site at a time as backend coverage
 * grows.
 *
 * Enable by setting `VITE_MOCK_MODE=false` and `VITE_API_BASE_URL=...`.
 */

import { apiService } from "@/services/api.service";
import { environmentService } from "@/services/environment.service";

export type Page<T> = {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
};

export interface ListQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
}

function q(input?: ListQuery): Record<string, string | number | undefined> {
  if (!input) return {};
  return {
    page: input.page,
    page_size: input.pageSize,
    search: input.search,
    sort_by: input.sortBy,
    sort_dir: input.sortDir,
  };
}

async function list<T>(path: string, params?: ListQuery): Promise<Page<T>> {
  return apiService.get<Page<T>>(path, { params: q(params) });
}

/* -------------------------------------------------------------------------- */
/* Users                                                                       */
/* -------------------------------------------------------------------------- */

export interface UserDto {
  id: string;
  email: string;
  fullName: string;
  avatarUrl: string | null;
  status: "active" | "suspended";
  roles: string[];
  defaultWorkspaceId: string | null;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
}

export const usersApi = {
  me: () => apiService.get<UserDto>("/users/me"),
  list: (query?: ListQuery) => list<UserDto>("/users", query),
  get: (id: string) => apiService.get<UserDto>(`/users/${id}`),
  update: (id: string, patch: Partial<Pick<UserDto, "fullName" | "avatarUrl">>) =>
    apiService.patch<UserDto>(`/users/${id}`, patch),
  remove: (id: string) => apiService.delete<{ deleted: boolean }>(`/users/${id}`),
  restore: (id: string) => apiService.post<UserDto>(`/users/${id}/restore`),
  bulkDelete: (ids: string[]) => apiService.post<{ deleted: number }>("/users/bulk-delete", { ids }),
};

/* -------------------------------------------------------------------------- */
/* Organizations                                                               */
/* -------------------------------------------------------------------------- */

export interface OrganizationDto {
  id: string;
  name: string;
  slug: string;
  type: string;
  status: string;
  website: string | null;
  contactEmail: string | null;
  memberCount: number;
  region: string | null;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
}

export const organizationsApi = {
  list: (query?: ListQuery) => list<OrganizationDto>("/organizations", query),
  get: (id: string) => apiService.get<OrganizationDto>(`/organizations/${id}`),
  create: (input: Partial<OrganizationDto> & { name: string; slug: string }) =>
    apiService.post<OrganizationDto>("/organizations", input),
  update: (id: string, patch: Partial<OrganizationDto>) =>
    apiService.patch<OrganizationDto>(`/organizations/${id}`, patch),
  remove: (id: string) => apiService.delete<{ deleted: boolean }>(`/organizations/${id}`),
  restore: (id: string) => apiService.post<OrganizationDto>(`/organizations/${id}/restore`),
};

/* -------------------------------------------------------------------------- */
/* Workspaces                                                                  */
/* -------------------------------------------------------------------------- */

export interface WorkspaceDto {
  id: string;
  organizationId: string;
  name: string;
  slug: string;
  plan: string;
  region: string;
  timezone: string;
  primaryLanguage: string;
  storageQuotaGb: number;
  apiQuotaMonthly: number;
  memberCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface WorkspaceMemberDto {
  userId: string;
  role: string;
  email: string | null;
  fullName: string | null;
}

export const workspacesApi = {
  list: (query?: ListQuery) => list<WorkspaceDto>("/workspaces", query),
  get: (id: string) => apiService.get<WorkspaceDto>(`/workspaces/${id}`),
  create: (input: Omit<WorkspaceDto, "id" | "memberCount" | "createdAt" | "updatedAt" | "storageQuotaGb" | "apiQuotaMonthly"> & Partial<WorkspaceDto>) =>
    apiService.post<WorkspaceDto>("/workspaces", input),
  update: (id: string, patch: Partial<WorkspaceDto>) =>
    apiService.patch<WorkspaceDto>(`/workspaces/${id}`, patch),
  remove: (id: string) => apiService.delete<{ deleted: boolean }>(`/workspaces/${id}`),
  members: (id: string) => apiService.get<{ items: WorkspaceMemberDto[] }>(`/workspaces/${id}/members`),
  addMember: (id: string, userId: string, role = "viewer") =>
    apiService.post<WorkspaceMemberDto>(`/workspaces/${id}/members`, { userId, role }),
  removeMember: (id: string, userId: string) =>
    apiService.delete<{ removed: boolean }>(`/workspaces/${id}/members/${userId}`),
  invite: (id: string, email: string, role = "viewer") =>
    apiService.post<{ invited: string }>(`/workspaces/${id}/invitations`, { email, role }),
  switch: (id: string) => apiService.post<{ workspaceId: string }>(`/workspaces/${id}/switch`),
};

/* -------------------------------------------------------------------------- */
/* Audience                                                                    */
/* -------------------------------------------------------------------------- */

export interface AudienceContactDto {
  id: string;
  workspaceId: string;
  fullName: string;
  email: string | null;
  phone: string | null;
  language: string;
  tags: string[];
  status: string;
  district: string | null;
  state: string | null;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
}

export const audienceApi = {
  list: (query?: ListQuery) => list<AudienceContactDto>("/audience", query),
  get: (id: string) => apiService.get<AudienceContactDto>(`/audience/${id}`),
  create: (input: Partial<AudienceContactDto> & { workspaceId: string; fullName: string }) =>
    apiService.post<AudienceContactDto>("/audience", input),
  update: (id: string, patch: Partial<AudienceContactDto>) =>
    apiService.patch<AudienceContactDto>(`/audience/${id}`, patch),
  remove: (id: string) => apiService.delete<{ deleted: boolean }>(`/audience/${id}`),
  restore: (id: string) => apiService.post<AudienceContactDto>(`/audience/${id}/restore`),
  bulkDelete: (ids: string[]) =>
    apiService.post<{ deleted: number }>("/audience/bulk-delete", { ids }),
  bulkUpdate: (payload: {
    ids: string[];
    status?: string;
    language?: string;
    addTags?: string[];
    removeTags?: string[];
  }) => apiService.post<{ updated: number }>("/audience/bulk-update", payload),
  duplicates: (workspaceId: string) =>
    apiService.get<{ items: Array<{ email: string; count: number }>; total: number }>(
      "/audience/duplicates",
      { params: { workspaceId } },
    ),
  exportCsvUrl: (workspaceId: string) => {
    const base = environmentService.get("API_BASE_URL");
    return `${base}/audience/export?workspaceId=${encodeURIComponent(workspaceId)}`;
  },
  async importCsv(workspaceId: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    const base = environmentService.get("API_BASE_URL");
    const res = await fetch(`${base}/audience/import?workspaceId=${encodeURIComponent(workspaceId)}`, {
      method: "POST",
      body: form,
      credentials: "include",
    });
    if (!res.ok) throw new Error(`Import failed: ${res.status}`);
    const json = (await res.json()) as { data: { created: number; skipped: number; errors: Array<{ row: number; error: string }> } };
    return json.data;
  },
};

/* -------------------------------------------------------------------------- */
/* Campaigns                                                                   */
/* -------------------------------------------------------------------------- */

export type CampaignStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "rejected"
  | "scheduled"
  | "published"
  | "archived";

export interface CampaignDto {
  id: string;
  workspaceId: string;
  name: string;
  status: CampaignStatus;
  channels: string[];
  audienceCount: number;
  startsAt: string | null;
  endsAt: string | null;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
}

export const campaignsApi = {
  list: (query?: ListQuery) => list<CampaignDto>("/campaigns", query),
  get: (id: string) => apiService.get<CampaignDto>(`/campaigns/${id}`),
  create: (input: Partial<CampaignDto> & { workspaceId: string; name: string }) =>
    apiService.post<CampaignDto>("/campaigns", input),
  update: (id: string, patch: Partial<CampaignDto>) =>
    apiService.patch<CampaignDto>(`/campaigns/${id}`, patch),
  remove: (id: string) => apiService.delete<{ deleted: boolean }>(`/campaigns/${id}`),
  restore: (id: string) => apiService.post<CampaignDto>(`/campaigns/${id}/restore`),
  submit: (id: string) => apiService.post<CampaignDto>(`/campaigns/${id}/submit`),
  approve: (id: string, note?: string) =>
    apiService.post<CampaignDto>(`/campaigns/${id}/approve`, { note }),
  reject: (id: string, note?: string) =>
    apiService.post<CampaignDto>(`/campaigns/${id}/reject`, { note }),
  schedule: (id: string, startsAt: string, endsAt?: string) =>
    apiService.post<CampaignDto>(`/campaigns/${id}/schedule`, { startsAt, endsAt }),
  publish: (id: string) => apiService.post<CampaignDto>(`/campaigns/${id}/publish`),
  archive: (id: string) => apiService.post<CampaignDto>(`/campaigns/${id}/archive`),
  clone: (id: string) => apiService.post<CampaignDto>(`/campaigns/${id}/clone`),
  approvals: (id: string) =>
    apiService.get<{
      items: Array<{
        id: string;
        status: string;
        reviewerId: string | null;
        note: string | null;
        createdAt: string;
      }>;
    }>(`/campaigns/${id}/approvals`),
};

/* -------------------------------------------------------------------------- */
/* Templates                                                                   */
/* -------------------------------------------------------------------------- */

export interface TemplateDto {
  id: string;
  workspaceId: string;
  name: string;
  category: string;
  channels: string[];
  language: string;
  version: number;
  status: string;
  body: string;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
}

export interface TemplateVersionDto {
  id: string;
  version: number;
  body: string;
  note: string | null;
  createdAt: string;
}

export const templatesApi = {
  list: (query?: ListQuery) => list<TemplateDto>("/templates", query),
  get: (id: string) => apiService.get<TemplateDto>(`/templates/${id}`),
  create: (input: Partial<TemplateDto> & { workspaceId: string; name: string }) =>
    apiService.post<TemplateDto>("/templates", input),
  update: (id: string, patch: Partial<TemplateDto>) =>
    apiService.patch<TemplateDto>(`/templates/${id}`, patch),
  remove: (id: string) => apiService.delete<{ deleted: boolean }>(`/templates/${id}`),
  restore: (id: string) => apiService.post<TemplateDto>(`/templates/${id}/restore`),
  clone: (id: string) => apiService.post<TemplateDto>(`/templates/${id}/clone`),
  versions: (id: string) =>
    apiService.get<{ items: TemplateVersionDto[] }>(`/templates/${id}/versions`),
  restoreVersion: (id: string, version: number) =>
    apiService.post<TemplateDto>(`/templates/${id}/versions/${version}/restore`),
  usage: (id: string) =>
    apiService.get<{ campaignCount: number }>(`/templates/${id}/usage`),
};

import { authBackend, securityBackend } from "./auth.backend";
import { aiBackend, translationBackend, communicationBackend, monitoringBackend } from "./engine.backend";
import {
  analyticsApi, reportsApi, searchApi, mediaApi, notificationsApi, monitoringExtrasApi,
} from "./insights.backend";

export {
  authBackend, securityBackend,
  aiBackend, translationBackend, communicationBackend, monitoringBackend,
  analyticsApi, reportsApi, searchApi, mediaApi, notificationsApi, monitoringExtrasApi,
};

export const backendApi = {
  auth: authBackend,
  security: securityBackend,
  ai: aiBackend,
  translation: translationBackend,
  communication: communicationBackend,
  monitoring: monitoringBackend,
  monitoringExtras: monitoringExtrasApi,
  users: usersApi,
  organizations: organizationsApi,
  workspaces: workspacesApi,
  audience: audienceApi,
  campaigns: campaignsApi,
  templates: templatesApi,
  analytics: analyticsApi,
  reports: reportsApi,
  search: searchApi,
  media: mediaApi,
  notifications: notificationsApi,
  isLive: () => !environmentService.isMock(),
};


