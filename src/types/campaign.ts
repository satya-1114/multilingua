import type { Paginated } from "@/types/common";

export type CampaignStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "scheduled"
  | "running"
  | "completed"
  | "cancelled"
  | "archived"
  | "failed";

export type CampaignPriority = "low" | "medium" | "high" | "critical";

export type CampaignType =
  | "awareness"
  | "advisory"
  | "emergency"
  | "notice"
  | "survey"
  | "event"
  | "internal"
  | "election"
  | "healthcare"
  | "education";

export type CampaignVisibility = "private" | "organization" | "public";

export type CampaignCategory =
  | "government"
  | "healthcare"
  | "education"
  | "ngo"
  | "corporate"
  | "emergency"
  | "election"
  | "custom";

export interface CampaignApprovalEntry {
  id: string;
  actorId: string;
  actorName: string;
  actorRole?: string;
  status: "pending" | "approved" | "rejected" | "sent_back";
  comment?: string;
  at: string;
}

export interface CampaignActivityEntry {
  id: string;
  type:
    | "created"
    | "updated"
    | "status_changed"
    | "submitted"
    | "approved"
    | "rejected"
    | "sent_back"
    | "launched"
    | "cancelled"
    | "archived"
    | "note"
    | "duplicated";
  message: string;
  actor: string;
  at: string;
  meta?: Record<string, unknown>;
}

export interface CampaignNote {
  id: string;
  body: string;
  authorId: string;
  authorName: string;
  pinned: boolean;
  createdAt: string;
}

export interface CampaignSchedule {
  mode: "draft" | "publish_now" | "schedule" | "recurring";
  timezone: string;
  startAt?: string;
  endAt?: string;
  expiresAt?: string;
  recurrenceRule?: string;
}

export interface Campaign {
  id: string;
  code: string;
  name: string;
  description?: string;
  objective?: string;
  type: CampaignType;
  category: CampaignCategory;
  priority: CampaignPriority;
  visibility: CampaignVisibility;
  status: CampaignStatus;
  color: string;
  icon?: string;
  tags: string[];
  organizationId: string;
  organizationName: string;
  department?: string;
  ownerId: string;
  ownerName: string;
  audienceGroupIds: string[];
  audienceContactIds: string[];
  estimatedReach: number;
  languages: string[];
  templateId?: string;
  templateName?: string;
  schedule: CampaignSchedule;
  approvals: CampaignApprovalEntry[];
  activity: CampaignActivityEntry[];
  notes: CampaignNote[];
  createdAt: string;
  updatedAt: string;
  launchedAt?: string;
  completedAt?: string;
  archivedAt?: string;
}

export interface CampaignInput {
  name: string;
  description?: string;
  objective?: string;
  type: CampaignType;
  category: CampaignCategory;
  priority: CampaignPriority;
  visibility: CampaignVisibility;
  color: string;
  icon?: string;
  tags: string[];
  organizationId: string;
  department?: string;
  ownerId: string;
  audienceGroupIds: string[];
  audienceContactIds: string[];
  languages: string[];
  templateId?: string;
  schedule: CampaignSchedule;
}

export interface CampaignListQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  status?: CampaignStatus[];
  type?: CampaignType[];
  priority?: CampaignPriority[];
  category?: CampaignCategory[];
  ownerId?: string;
  organizationId?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
  from?: string;
  to?: string;
}

export interface CampaignStats {
  total: number;
  draft: number;
  scheduled: number;
  running: number;
  completed: number;
  archived: number;
  failed: number;
  cancelled: number;
  pendingApproval: number;
  monthly: { month: string; count: number }[];
  byType: { type: CampaignType; value: number }[];
  performance: { name: string; delivered: number; opened: number; failed: number }[];
  trend: { day: string; delivered: number }[];
}

export type CampaignPage = Paginated<Campaign>;
