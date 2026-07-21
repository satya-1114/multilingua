export const RESOURCE_TYPES = [
  "disaster",
  "campaign",
  "volunteer_recruitment",
  "emergency_info",
  "donation",
  "organization",
  "other",
] as const;
export type ResourceType = (typeof RESOURCE_TYPES)[number];

export const VISIBILITIES = [
  "public",
  "unlisted",
  "private",
  "expired",
  "disabled",
] as const;
export type Visibility = (typeof VISIBILITIES)[number];

export const QR_STATUSES = ["pending", "active", "revoked", "expired"] as const;
export type QRStatus = (typeof QR_STATUSES)[number];

export const QR_FORMATS = ["png", "svg", "pdf"] as const;
export type QRFormat = (typeof QR_FORMATS)[number];

export type DeviceType = "mobile" | "tablet" | "desktop" | "bot" | "unknown";

export interface PublicResource {
  id: string;
  resourceType: ResourceType;
  resourceId: string | null;
  slug: string;
  qrToken: string | null;
  title: string;
  description: string | null;
  visibility: Visibility;
  expiresAt: string | null;
  organizationId: string | null;
  createdByUserId: string | null;
  metadata: Record<string, unknown>;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface PublicResourceCreateInput {
  resourceType: ResourceType;
  resourceId?: string | null;
  slug: string;
  title: string;
  description?: string | null;
  visibility?: Visibility;
  expiresAt?: string | null;
  organizationId?: string | null;
  metadata?: Record<string, unknown>;
}

export interface PublicResourceUpdateInput {
  slug?: string;
  title?: string;
  description?: string | null;
  visibility?: Visibility;
  expiresAt?: string | null;
  organizationId?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface PublicResourceListQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  resourceType?: ResourceType;
  visibility?: Visibility;
  organizationId?: string;
  resourceId?: string;
  activeOnly?: boolean;
  sortBy?: string;
  sortDir?: "asc" | "desc";
}

export interface QRCode {
  id: string;
  publicResourceId: string;
  format: QRFormat;
  version: number;
  status: QRStatus;
  generatedAt: string | null;
  metadata: Record<string, unknown>;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface QRCodeCreateInput {
  format?: QRFormat;
  version?: number;
  metadata?: Record<string, unknown>;
}

export interface PublicView {
  id: string;
  publicResourceId: string;
  viewedAt: string;
  ipHash: string | null;
  userAgentHash: string | null;
  country: string | null;
  deviceType: DeviceType | null;
  referrer: string | null;
}

export interface PublicViewSummary {
  total: number;
  byCountry?: Record<string, number>;
  byDevice?: Record<string, number>;
  [k: string]: unknown;
}
