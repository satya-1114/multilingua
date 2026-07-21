import type { ChannelKind } from "./channel";

export type DeliveryStatus =
  | "queued"
  | "scheduled"
  | "processing"
  | "sent"
  | "delivered"
  | "opened"
  | "clicked"
  | "responded"
  | "failed"
  | "bounced"
  | "cancelled"
  | "retrying"
  | "paused";

export type DeliveryQueueKind =
  | "delivery"
  | "scheduled"
  | "retry"
  | "failed"
  | "processing"
  | "cancelled"
  | "completed";

export type DeliveryPriority = "low" | "normal" | "high" | "urgent";

export interface DeliveryRecipient {
  id: string;
  contactId: string;
  name: string;
  address: string;
  language: string;
  channel: ChannelKind;
  status: DeliveryStatus;
  attempts: number;
  lastAttemptAt?: string;
  deliveredAt?: string;
  openedAt?: string;
  clickedAt?: string;
  respondedAt?: string;
  failureCategory?: FailureCategory;
  failureReason?: string;
  device?: string;
}

export type FailureCategory =
  | "invalid_address"
  | "bounced"
  | "rate_limited"
  | "provider_error"
  | "unsubscribed"
  | "blocked"
  | "timeout"
  | "unknown";

export interface DeliveryJob {
  id: string;
  campaignId: string;
  campaignName: string;
  channel: ChannelKind;
  status: DeliveryStatus;
  priority: DeliveryPriority;
  totalRecipients: number;
  delivered: number;
  failed: number;
  pending: number;
  opened: number;
  clicked: number;
  responded: number;
  scheduledAt?: string;
  startedAt?: string;
  completedAt?: string;
  language: string;
  organizationId: string;
  ownerId: string;
  attempts: number;
  maxAttempts: number;
  createdAt: string;
  updatedAt: string;
}

export interface DeliveryQueueSnapshot {
  kind: DeliveryQueueKind;
  label: string;
  count: number;
  throughputPerMinute: number;
  oldestAgeSeconds: number;
  jobs: DeliveryJob[];
}

export interface DeliveryListQuery {
  search?: string;
  status?: DeliveryStatus[];
  channel?: ChannelKind[];
  priority?: DeliveryPriority[];
  campaignId?: string;
  from?: string;
  to?: string;
  page?: number;
  pageSize?: number;
}

export interface DeliveryActionResult {
  ok: boolean;
  message: string;
}
