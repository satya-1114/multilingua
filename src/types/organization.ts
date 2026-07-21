import type { OrganizationType } from "@/constants/rbac";

export type OrganizationStatus = "active" | "inactive" | "suspended";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  type: OrganizationType;
  logoUrl?: string;
  website?: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  pincode?: string;
  timezone: string;
  languages: string[];
  primaryAdminId?: string;
  primaryAdminName?: string;
  status: OrganizationStatus;
  audienceCount: number;
  userCount: number;
  campaignCount: number;
  brandColor?: string;
  createdAt: string;
  updatedAt: string;
}

export interface OrganizationInput {
  name: string;
  type: OrganizationType;
  website?: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  country: string;
  pincode?: string;
  timezone: string;
  languages: string[];
  primaryAdminId?: string;
  status: OrganizationStatus;
  brandColor?: string;
  logoUrl?: string;
}

export interface OrganizationStats {
  total: number;
  active: number;
  inactive: number;
  suspended: number;
  byType: { type: string; value: number }[];
}
