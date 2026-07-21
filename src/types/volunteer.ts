/**
 * Volunteer & Task types.
 *
 * Shapes align with the future FastAPI backend. UI-only fields are optional;
 * services return whatever the backend delivers. No hardcoded business logic.
 */

export type VolunteerStatus =
  | "available"
  | "busy"
  | "on_leave"
  | "inactive";

export interface Volunteer {
  id: string;
  userId: string;
  organizationId?: string | null;
  fullName: string;
  email: string;
  phone?: string;
  avatarUrl?: string | null;
  languages: string[];
  skills: string[];
  currentLocation: string;
  availability: string;
  status: VolunteerStatus;
  assignedCampaignIds: string[];
  completedTaskCount: number;
  activeTaskCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface VolunteerListQuery {
  search?: string;
  language?: string;
  skill?: string;
  location?: string;
  availability?: string;
  status?: VolunteerStatus;
  taskStatus?: TaskStatus;
  sortBy?: "fullName" | "createdAt" | "activeTaskCount" | "completedTaskCount";
  sortDir?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

export type TaskStatus =
  | "pending"
  | "accepted"
  | "in_progress"
  | "completed"
  | "rejected"
  | "cancelled";

export type TaskPriority = "low" | "medium" | "high" | "urgent";

export interface VolunteerTask {
  id: string;
  volunteerId: string;
  volunteerName?: string;
  campaignId: string;
  campaignName?: string;
  title: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  assignedAt: string;
  dueAt?: string;
  completedAt?: string;
  createdBy?: string;
  updatedAt: string;
}

export interface TaskInput {
  volunteerId: string;
  campaignId: string;
  title: string;
  description: string;
  priority: TaskPriority;
  dueAt?: string;
}

export interface TaskListQuery {
  volunteerId?: string;
  campaignId?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  search?: string;
  page?: number;
  pageSize?: number;
}
