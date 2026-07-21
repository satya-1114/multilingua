import type { Paginated } from "@/types/common";

/**
 * Disaster Management domain types.
 *
 * Mirrors backend contract exposed under `/api/v1/disasters` — see
 * `backend/app/schemas/disaster.py`. Field names follow the camelCase
 * envelope emitted by the FastAPI serializers.
 */

export const DISASTER_TYPES = [
  "flood",
  "fire",
  "cyclone",
  "earthquake",
  "landslide",
  "heatwave",
  "medical",
  "industrial",
  "public_safety",
  "other",
] as const;
export type DisasterType = (typeof DISASTER_TYPES)[number];

export const DISASTER_SEVERITIES = ["low", "medium", "high", "critical"] as const;
export type DisasterSeverity = (typeof DISASTER_SEVERITIES)[number];

export const DISASTER_STATUSES = [
  "reported",
  "verified",
  "active",
  "contained",
  "resolved",
  "closed",
] as const;
export type DisasterStatus = (typeof DISASTER_STATUSES)[number];

export const ASSIGNMENT_STATUSES = [
  "assigned",
  "accepted",
  "in_progress",
  "completed",
  "cancelled",
] as const;
export type AssignmentStatus = (typeof ASSIGNMENT_STATUSES)[number];

export const ATTACHMENT_KINDS = ["image", "document", "evidence"] as const;
export type AttachmentKind = (typeof ATTACHMENT_KINDS)[number];

export interface Disaster {
  id: string;
  title: string;
  description?: string | null;
  disasterType: DisasterType;
  severity: DisasterSeverity;
  status: DisasterStatus;
  latitude?: number | null;
  longitude?: number | null;
  address?: string | null;
  city?: string | null;
  district?: string | null;
  state?: string | null;
  country?: string | null;
  postalCode?: string | null;
  startedAt?: string | null;
  resolvedAt?: string | null;
  organizationId?: string | null;
  createdByUserId?: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface DisasterInput {
  title: string;
  description?: string;
  disasterType: DisasterType;
  severity?: DisasterSeverity;
  status?: DisasterStatus;
  latitude?: number;
  longitude?: number;
  address?: string;
  city?: string;
  district?: string;
  state?: string;
  country?: string;
  postalCode?: string;
  startedAt?: string;
  organizationId?: string;
  metadata?: Record<string, unknown>;
}

export type DisasterUpdate = Partial<DisasterInput> & {
  resolvedAt?: string;
};

export interface DisasterListQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  disasterType?: DisasterType;
  severity?: DisasterSeverity;
  status?: DisasterStatus;
  organizationId?: string;
  city?: string;
  district?: string;
  state?: string;
  country?: string;
  volunteerId?: string;
  sortBy?: "startedAt" | "severity" | "status" | "updatedAt" | "title" | "createdAt";
  sortDir?: "asc" | "desc";
}

export interface DisasterAssignment {
  id: string;
  disasterId: string;
  volunteerId: string;
  volunteerName?: string | null;
  assignedByUserId?: string | null;
  role?: string | null;
  status: AssignmentStatus;
  notes?: string | null;
  assignedAt?: string | null;
  completedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AssignmentCreateInput {
  volunteerId: string;
  role?: string;
  notes?: string;
}

export interface DisasterAttachment {
  id: string;
  disasterId: string;
  uploadedByUserId?: string | null;
  kind: AttachmentKind;
  fileName: string;
  fileUrl: string;
  contentType?: string | null;
  sizeBytes?: number | null;
  caption?: string | null;
  createdAt: string;
}

export interface AttachmentCreateInput {
  kind?: AttachmentKind;
  fileName: string;
  fileUrl: string;
  contentType?: string;
  sizeBytes?: number;
  caption?: string;
}

export type DisasterPage = Paginated<Disaster>;

/**
 * Placeholder — the backend does not yet expose a public alerts endpoint.
 * The public route uses this shape and will surface a friendly notice at
 * runtime until the backend contract lands.
 */
export interface PublicDisasterAlert {
  id: string;
  slug: string;
  title: string;
  description?: string;
  disasterType: DisasterType;
  severity: DisasterSeverity;
  status: DisasterStatus;
  startedAt?: string;
  resolvedAt?: string;
  address?: string;
  languages: string[];
  updatedAt: string;
}
