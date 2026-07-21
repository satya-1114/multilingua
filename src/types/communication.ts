import type { ChannelKind } from "./channel";
import type { DeliveryJob, DeliveryStatus, FailureCategory } from "./delivery";

export interface CommunicationKpis {
  sent: number;
  delivered: number;
  failed: number;
  queued: number;
  scheduled: number;
  openRate: number;
  clickRate: number;
  responseRate: number;
  bounceRate: number;
  deliverySuccessRate: number;
}

export interface TimeseriesPoint {
  date: string;
  value: number;
  secondary?: number;
}

export interface DistributionSlice {
  label: string;
  value: number;
}

export interface FailureBreakdown {
  category: FailureCategory;
  label: string;
  count: number;
  share: number;
}

export interface CommunicationOverview {
  kpis: CommunicationKpis;
  deliveryTimeline: TimeseriesPoint[];
  channelDistribution: DistributionSlice[];
  languageDistribution: DistributionSlice[];
  dailyTrend: TimeseriesPoint[];
  engagement: TimeseriesPoint[];
  failureBreakdown: FailureBreakdown[];
  recentDeliveries: DeliveryJob[];
  recentFailures: DeliveryJob[];
  upcomingScheduled: DeliveryJob[];
}

export interface CommunicationTimelineEvent {
  id: string;
  step:
    | "created"
    | "approved"
    | "scheduled"
    | "sent"
    | "delivered"
    | "opened"
    | "clicked"
    | "responded"
    | "completed"
    | "failed";
  at: string;
  actor?: string;
  note?: string;
  channel?: ChannelKind;
  status?: DeliveryStatus;
}

export interface NotificationChannelPreference {
  enabled: boolean;
  digest: "off" | "daily" | "weekly";
  quietHours: { start: string; end: string; enabled: boolean };
}

export interface NotificationPreferences {
  userId: string;
  email: NotificationChannelPreference;
  sms: NotificationChannelPreference;
  push: NotificationChannelPreference;
  inApp: NotificationChannelPreference;
  emergencyOverride: boolean;
  language: string;
  updatedAt: string;
}
