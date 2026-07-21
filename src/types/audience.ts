import type { CommunicationChannel, Gender } from "@/constants/india";

export type AudienceStatus = "active" | "inactive" | "pending" | "opted_out";

export interface AudienceTagRef {
  id: string;
  name: string;
  color: string;
}

export interface AudienceContact {
  id: string;
  firstName: string;
  lastName: string;
  fullName: string;
  email: string;
  phone: string;
  alternatePhone?: string;
  dateOfBirth?: string;
  gender?: Gender;
  occupation?: string;
  organizationId?: string;
  organizationName?: string;
  department?: string;
  state: string;
  district: string;
  city: string;
  address?: string;
  pincode?: string;
  preferredLanguage: string;
  preferredChannel: CommunicationChannel;
  tags: AudienceTagRef[];
  groupIds: string[];
  status: AudienceStatus;
  notes?: string;
  avatarUrl?: string;
  consentGiven: boolean;
  createdAt: string;
  updatedAt: string;
  deletedAt?: string | null;
}

export interface AudienceInput {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  alternatePhone?: string;
  dateOfBirth?: string;
  gender?: Gender;
  occupation?: string;
  organizationId?: string;
  department?: string;
  state: string;
  district: string;
  city: string;
  address?: string;
  pincode?: string;
  preferredLanguage: string;
  preferredChannel: CommunicationChannel;
  tagIds?: string[];
  groupIds?: string[];
  status: AudienceStatus;
  notes?: string;
  avatarUrl?: string;
  consentGiven: boolean;
}

export interface AudienceGroup {
  id: string;
  name: string;
  description?: string;
  memberCount: number;
  createdAt: string;
  updatedAt: string;
  color: string;
}

export interface AudienceTag {
  id: string;
  name: string;
  color: string;
  audienceCount: number;
  createdAt: string;
}

export interface AudienceStats {
  total: number;
  active: number;
  inactive: number;
  recentlyAdded: number;
  languageDistribution: { language: string; value: number }[];
  stateDistribution: { state: string; value: number }[];
  channelDistribution: { channel: string; value: number }[];
}

export interface AudienceActivityEvent {
  id: string;
  type: "created" | "updated" | "consent" | "campaign_delivered" | "campaign_opened" | "tag_added" | "group_joined";
  message: string;
  actor?: string;
  at: string;
}

export interface AudienceListQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  sortBy?: keyof AudienceContact | string;
  sortDir?: "asc" | "desc";
  status?: AudienceStatus[];
  states?: string[];
  languages?: string[];
  channels?: string[];
  tagIds?: string[];
  groupIds?: string[];
}
