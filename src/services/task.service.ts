import { apiService } from "./api.service";
import type {
  TaskInput,
  TaskListQuery,
  TaskStatus,
  VolunteerTask,
} from "@/types/volunteer";

/**
 * Volunteer Task service.
 *
 * Backend endpoints (see backend/app/api/v1/tasks.py):
 *   GET    /tasks                     list (paginated envelope; items only used)
 *   GET    /tasks/mine                current volunteer's tasks
 *   POST   /tasks                     assign
 *   PATCH  /tasks/:id                 edit assignment
 *   POST   /tasks/:id/assign          reassign to another volunteer
 *   PATCH  /tasks/:id/status          status transition
 *   POST   /tasks/:id/complete        mark completed
 *   DELETE /tasks/:id                 cancel assignment
 */
export const taskService = {
  list(query: TaskListQuery = {}): Promise<VolunteerTask[]> {
    return apiService.get<VolunteerTask[]>("/tasks", {
      params: query as Record<string, string | number | boolean | undefined>,
    });
  },

  mine(status?: TaskStatus): Promise<VolunteerTask[]> {
    return apiService.get<VolunteerTask[]>("/tasks/mine", {
      params: status ? { status } : undefined,
    });
  },

  assign(input: TaskInput): Promise<VolunteerTask> {
    return apiService.post<VolunteerTask>("/tasks", input);
  },

  update(id: string, patch: Partial<TaskInput>): Promise<VolunteerTask> {
    return apiService.patch<VolunteerTask>(`/tasks/${id}`, patch);
  },

  reassign(id: string, volunteerId: string): Promise<VolunteerTask> {
    return apiService.post<VolunteerTask>(`/tasks/${id}/assign`, { volunteerId });
  },

  setStatus(id: string, status: TaskStatus): Promise<VolunteerTask> {
    return apiService.patch<VolunteerTask>(`/tasks/${id}/status`, { status });
  },

  complete(id: string): Promise<VolunteerTask> {
    return apiService.post<VolunteerTask>(`/tasks/${id}/complete`);
  },

  cancel(id: string): Promise<void> {
    return apiService.delete<void>(`/tasks/${id}`);
  },
};
