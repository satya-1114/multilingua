export interface StatMetric {
  key: string;
  label: string;
  value: string;
  delta: string;
  trend: "up" | "down" | "flat";
  helper: string;
}

export interface CampaignSummary {
  id: string;
  name: string;
  channel: string;
  status: "draft" | "scheduled" | "running" | "completed" | "paused";
  scheduledFor: string;
  languages: number;
  audience: number;
  progress: number;
}

export interface ActivityEntry {
  id: string;
  actorName: string;
  actorInitials: string;
  action: string;
  target: string;
  timestamp: string;
  category: "campaign" | "content" | "audience" | "system";
}

export interface AudienceSegment {
  id: string;
  name: string;
  size: number;
  region: string;
  languages: string[];
  updatedAt: string;
}

export interface Announcement {
  id: string;
  title: string;
  body: string;
  publishedAt: string;
  tag: string;
}

export interface DashboardOverview {
  stats: StatMetric[];
  upcoming: CampaignSummary[];
  activity: ActivityEntry[];
  audience: AudienceSegment[];
  announcements: Announcement[];
  languageDistribution: { language: string; value: number }[];
  campaignStatus: { status: string; value: number }[];
  audienceGrowth: { month: string; audience: number; engaged: number }[];
  deliveryTrend: { day: string; delivered: number; engaged: number }[];
}
