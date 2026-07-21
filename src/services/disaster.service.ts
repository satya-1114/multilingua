import { apiService } from "./api.service";
import { httpClient } from "@/api/client/http-client";
import type { Paginated } from "@/types/common";
import type {
  AssignmentCreateInput,
  AssignmentStatus,
  AttachmentCreateInput,
  Disaster,
  DisasterAssignment,
  DisasterAttachment,
  DisasterInput,
  DisasterListQuery,
  DisasterUpdate,
  PublicDisasterAlert,
} from "@/types/disaster";

/**
 * Disaster Management service.
 *
 * Thin facade over the existing `apiService` — no duplicate HTTP layer.
 * Backend contract: see `backend/app/api/v1/disasters.py`. All routes are
 * mounted at `/disasters` under `VITE_API_BASE_URL` (e.g. `/api/v1`).
 */
export const disasterService = {
  async list(query: DisasterListQuery = {}): Promise<Paginated<Disaster>> {
    const env = await httpClient.request<Disaster[]>({
      method: "GET",
      path: "/disasters",
      params: query as Record<string, string | number | boolean | undefined>,
    });
    const items = Array.isArray(env.data) ? env.data : [];
    const pg = env.pagination;
    return {
      items,
      total: pg?.total ?? items.length,
      page: pg?.page ?? query.page ?? 1,
      pageSize: pg?.pageSize ?? query.pageSize ?? items.length,
    };
  },

  get(id: string): Promise<Disaster> {
    return apiService.get<Disaster>(`/disasters/${id}`);
  },

  create(input: DisasterInput): Promise<Disaster> {
    return apiService.post<Disaster>("/disasters", input);
  },

  update(id: string, patch: DisasterUpdate): Promise<Disaster> {
    return apiService.patch<Disaster>(`/disasters/${id}`, patch);
  },

  // ── Lifecycle transitions ───────────────────────────────────────────────
  verify(id: string): Promise<Disaster> {
    return apiService.post<Disaster>(`/disasters/${id}/verify`);
  },
  activate(id: string): Promise<Disaster> {
    return apiService.post<Disaster>(`/disasters/${id}/activate`);
  },
  contain(id: string): Promise<Disaster> {
    return apiService.post<Disaster>(`/disasters/${id}/contain`);
  },
  resolve(id: string, resolvedAt?: string): Promise<Disaster> {
    return apiService.post<Disaster>(`/disasters/${id}/resolve`,
      resolvedAt ? { resolvedAt } : {});
  },
  close(id: string): Promise<Disaster> {
    return apiService.post<Disaster>(`/disasters/${id}/close`);
  },
  reopen(id: string): Promise<Disaster> {
    return apiService.post<Disaster>(`/disasters/${id}/reopen`);
  },

  // ── Assignments ─────────────────────────────────────────────────────────
  assignments(id: string, status?: AssignmentStatus): Promise<DisasterAssignment[]> {
    return apiService.get<DisasterAssignment[]>(`/disasters/${id}/assignments`,
      status ? { params: { status } } : undefined);
  },
  assignVolunteer(id: string, payload: AssignmentCreateInput): Promise<DisasterAssignment> {
    return apiService.post<DisasterAssignment>(`/disasters/${id}/assignments`, payload);
  },
  updateAssignment(
    assignmentId: string,
    patch: { role?: string; notes?: string },
  ): Promise<DisasterAssignment> {
    return apiService.patch<DisasterAssignment>(
      `/disasters/assignments/${assignmentId}`,
      patch,
    );
  },
  reassignAssignment(assignmentId: string, volunteerId: string): Promise<DisasterAssignment> {
    return apiService.post<DisasterAssignment>(
      `/disasters/assignments/${assignmentId}/reassign`,
      { volunteerId },
    );
  },
  setAssignmentStatus(
    assignmentId: string,
    status: AssignmentStatus,
    notes?: string,
  ): Promise<DisasterAssignment> {
    return apiService.patch<DisasterAssignment>(
      `/disasters/assignments/${assignmentId}/status`,
      { status, notes },
    );
  },
  completeAssignment(assignmentId: string, notes?: string): Promise<DisasterAssignment> {
    return apiService.post<DisasterAssignment>(
      `/disasters/assignments/${assignmentId}/complete`,
      notes ? { notes } : {},
    );
  },
  cancelAssignment(assignmentId: string): Promise<DisasterAssignment> {
    return apiService.delete<DisasterAssignment>(
      `/disasters/assignments/${assignmentId}`,
    );
  },

  // ── Attachments (metadata only — no upload storage) ─────────────────────
  attachments(id: string, kind?: string): Promise<DisasterAttachment[]> {
    return apiService.get<DisasterAttachment[]>(`/disasters/${id}/attachments`,
      kind ? { params: { kind } } : undefined);
  },
  registerAttachment(id: string, payload: AttachmentCreateInput): Promise<DisasterAttachment> {
    return apiService.post<DisasterAttachment>(`/disasters/${id}/attachments`, payload);
  },
  deleteAttachment(attachmentId: string): Promise<void> {
    return apiService.delete<void>(`/disasters/attachments/${attachmentId}`);
  },

  // ── Public alert (backend not yet implemented — returns a friendly error) ─
  publicAlert(_slug: string, _params?: { language?: string }): Promise<PublicDisasterAlert> {
    return Promise.reject(
      new Error("Public disaster alerts are not yet available."),
    );
  },
};
