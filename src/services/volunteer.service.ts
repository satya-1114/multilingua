import { apiService } from "./api.service";
import { httpClient } from "@/api/client/http-client";
import type { Paginated } from "@/types/common";
import type {
  Volunteer,
  VolunteerListQuery,
  VolunteerStatus,
  VolunteerTask,
} from "@/types/volunteer";

/**
 * Volunteer service.
 *
 * Backend endpoints (see backend/app/api/v1/volunteers.py):
 *   GET    /volunteers                          list (paginated envelope)
 *   GET    /volunteers/:id                      profile
 *   GET    /volunteers/:id/tasks                task history
 *   POST   /volunteers                          create
 *   PATCH  /volunteers/:id                      update profile / partial
 *   POST   /volunteers/:id/activate             set status=available
 *   POST   /volunteers/:id/deactivate           set status=inactive
 *   POST   /volunteers/:id/organization         assign / clear organization
 */
export const volunteerService = {
  async list(query: VolunteerListQuery = {}): Promise<Paginated<Volunteer>> {
    const env = await httpClient.request<Volunteer[]>({
      method: "GET",
      path: "/volunteers",
      params: query as Record<string, string | number | boolean | undefined>,
    });
    const items = Array.isArray(env.data) ? (env.data as Volunteer[]) : [];
    const pg = env.pagination;
    return {
      items,
      total: pg?.total ?? items.length,
      page: pg?.page ?? query.page ?? 1,
      pageSize: pg?.pageSize ?? query.pageSize ?? items.length,
    };
  },

  get(id: string): Promise<Volunteer> {
    return apiService.get<Volunteer>(`/volunteers/${id}`);
  },

  tasks(id: string): Promise<VolunteerTask[]> {
    return apiService.get<VolunteerTask[]>(`/volunteers/${id}/tasks`);
  },

  create(payload: Partial<Volunteer> & { userId: string }): Promise<Volunteer> {
    return apiService.post<Volunteer>("/volunteers", payload);
  },

  update(id: string, patch: Partial<Volunteer>): Promise<Volunteer> {
    return apiService.patch<Volunteer>(`/volunteers/${id}`, patch);
  },

  activate(id: string): Promise<Volunteer> {
    return apiService.post<Volunteer>(`/volunteers/${id}/activate`);
  },

  deactivate(id: string): Promise<Volunteer> {
    return apiService.post<Volunteer>(`/volunteers/${id}/deactivate`);
  },

  assignOrganization(id: string, organizationId: string | null): Promise<Volunteer> {
    return apiService.post<Volunteer>(`/volunteers/${id}/organization`, {
      organizationId,
    });
  },

  updateStatus(id: string, status: VolunteerStatus): Promise<Volunteer> {
    if (status === "available") return this.activate(id);
    if (status === "inactive") return this.deactivate(id);
    return apiService.patch<Volunteer>(`/volunteers/${id}`, { status });
  },
};
