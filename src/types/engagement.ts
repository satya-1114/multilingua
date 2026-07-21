import type { ChannelKind } from "./channel";

export interface EngagementMetrics {
  opens: number;
  clicks: number;
  replies: number;
  shares: number;
  downloads: number;
  registrations: number;
  attendance: number;
  participation: number;
  sentimentScore: number;
}

export interface EngagementHeatCell {
  day: string; // Mon-Sun
  hour: number; // 0-23
  value: number;
}

export interface EngagementComparison {
  label: string;
  opens: number;
  clicks: number;
  replies: number;
}

export interface EngagementTrendPoint {
  date: string;
  opens: number;
  clicks: number;
  replies: number;
}

export interface EngagementOverview {
  metrics: EngagementMetrics;
  heatmap: EngagementHeatCell[];
  trends: EngagementTrendPoint[];
  channelComparison: EngagementComparison[];
  languageComparison: EngagementComparison[];
  audienceComparison: EngagementComparison[];
}

export interface EngagementReport {
  id: string;
  name: string;
  scope: "channel" | "language" | "campaign" | "audience" | "delivery" | "organization";
  createdAt: string;
  createdBy: string;
  filters: { channel?: ChannelKind; language?: string; from?: string; to?: string };
}
