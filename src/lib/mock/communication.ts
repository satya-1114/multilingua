import type { Channel, ChannelKind } from "@/types/channel";
import type {
  DeliveryJob,
  DeliveryQueueSnapshot,
  DeliveryRecipient,
  DeliveryStatus,
} from "@/types/delivery";
import type {
  CommunicationOverview,
  NotificationPreferences,
  CommunicationTimelineEvent,
} from "@/types/communication";
import type { EngagementOverview, EngagementReport } from "@/types/engagement";
import type { ScheduleConfig } from "@/types/scheduler";
import type { RetryPolicy } from "@/types/retry-policy";

const now = new Date();
const iso = (offsetMinutes: number) =>
  new Date(now.getTime() + offsetMinutes * 60_000).toISOString();

const days = (n: number): string[] =>
  Array.from({ length: n }, (_, i) => {
    const d = new Date(now);
    d.setDate(d.getDate() - (n - 1 - i));
    return d.toISOString().slice(0, 10);
  });

export const mockChannels: Channel[] = [
  {
    id: "chn-email",
    kind: "email",
    name: "Transactional Email",
    provider: "AWS SES",
    status: "active",
    sender: { displayName: "Government of India · Public Alerts", address: "alerts@gov.in", verified: true },
    limits: { perMinute: 500, perHour: 20_000, perDay: 200_000, perMonth: 4_000_000 },
    usage: { dailySent: 84_320, dailyCap: 200_000, monthlySent: 1_842_902, monthlyCap: 4_000_000 },
    queueDepth: 1_284,
    retry: { policyId: "rp-email", maxAttempts: 5, intervalSeconds: 60 },
    health: { score: 98, latencyMs: 142, successRate: 99.2, errorRate: 0.8, lastCheckedAt: iso(-2), incidents24h: 0 },
    configuration: { region: "ap-south-1", pool: "primary" },
    createdAt: iso(-60 * 24 * 60),
    updatedAt: iso(-30),
  },
  {
    id: "chn-sms",
    kind: "sms",
    name: "Bulk SMS",
    provider: "Airtel IQ",
    status: "active",
    sender: { displayName: "MOHFW", address: "MOHFW", verified: true },
    limits: { perMinute: 2_000, perHour: 80_000, perDay: 1_500_000, perMonth: 30_000_000 },
    usage: { dailySent: 412_004, dailyCap: 1_500_000, monthlySent: 8_902_312, monthlyCap: 30_000_000 },
    queueDepth: 5_912,
    retry: { policyId: "rp-sms", maxAttempts: 3, intervalSeconds: 30 },
    health: { score: 92, latencyMs: 380, successRate: 97.4, errorRate: 2.6, lastCheckedAt: iso(-3), incidents24h: 1 },
    configuration: { entityId: "1102XXXXXX", templateApproved: "true" },
    createdAt: iso(-90 * 24 * 60),
    updatedAt: iso(-15),
  },
  {
    id: "chn-whatsapp",
    kind: "whatsapp",
    name: "WhatsApp Business",
    provider: "Meta Cloud API",
    status: "active",
    sender: { displayName: "Health Ministry", address: "+91-98XXXXXX40", verified: true },
    limits: { perMinute: 250, perHour: 10_000, perDay: 100_000, perMonth: 2_000_000 },
    usage: { dailySent: 22_419, dailyCap: 100_000, monthlySent: 512_802, monthlyCap: 2_000_000 },
    queueDepth: 214,
    retry: { policyId: "rp-whatsapp", maxAttempts: 4, intervalSeconds: 45 },
    health: { score: 96, latencyMs: 210, successRate: 98.6, errorRate: 1.4, lastCheckedAt: iso(-1), incidents24h: 0 },
    configuration: { wabaId: "1035XXXX", tier: "1M" },
    createdAt: iso(-45 * 24 * 60),
    updatedAt: iso(-8),
  },
  {
    id: "chn-push",
    kind: "push",
    name: "Mobile Push",
    provider: "Firebase Cloud Messaging",
    status: "active",
    sender: { displayName: "Aarogya Setu", address: "app.arogya.push", verified: true },
    limits: { perMinute: 5_000, perHour: 200_000, perDay: 3_000_000, perMonth: 60_000_000 },
    usage: { dailySent: 190_442, dailyCap: 3_000_000, monthlySent: 3_209_812, monthlyCap: 60_000_000 },
    queueDepth: 812,
    retry: { policyId: "rp-push", maxAttempts: 2, intervalSeconds: 15 },
    health: { score: 99, latencyMs: 82, successRate: 99.7, errorRate: 0.3, lastCheckedAt: iso(-1), incidents24h: 0 },
    configuration: { projectId: "arogya-alerts", pool: "standard" },
    createdAt: iso(-120 * 24 * 60),
    updatedAt: iso(-12),
  },
  {
    id: "chn-web",
    kind: "web_broadcast",
    name: "Website Broadcast",
    provider: "Platform Broadcast",
    status: "active",
    sender: { displayName: "portal.gov.in", address: "portal.gov.in", verified: true },
    limits: { perMinute: 100_000, perHour: 500_000, perDay: 5_000_000, perMonth: 100_000_000 },
    usage: { dailySent: 12_002, dailyCap: 5_000_000, monthlySent: 320_100, monthlyCap: 100_000_000 },
    queueDepth: 12,
    retry: { policyId: "rp-web", maxAttempts: 1, intervalSeconds: 10 },
    health: { score: 100, latencyMs: 20, successRate: 100, errorRate: 0, lastCheckedAt: iso(-1), incidents24h: 0 },
    configuration: { cdn: "cloudfront" },
    createdAt: iso(-30 * 24 * 60),
    updatedAt: iso(-5),
  },
  {
    id: "chn-social",
    kind: "social_broadcast",
    name: "Social Broadcast",
    provider: "X · Meta · YouTube",
    status: "degraded",
    sender: { displayName: "@GoIHealth", address: "@GoIHealth", verified: true },
    limits: { perMinute: 60, perHour: 500, perDay: 2_500, perMonth: 60_000 },
    usage: { dailySent: 208, dailyCap: 2_500, monthlySent: 4_912, monthlyCap: 60_000 },
    queueDepth: 42,
    retry: { policyId: "rp-social", maxAttempts: 3, intervalSeconds: 90 },
    health: { score: 74, latencyMs: 640, successRate: 91.2, errorRate: 8.8, lastCheckedAt: iso(-4), incidents24h: 2 },
    configuration: { networks: "x,facebook,youtube" },
    createdAt: iso(-15 * 24 * 60),
    updatedAt: iso(-30),
  },
  {
    id: "chn-voice",
    kind: "voice",
    name: "Voice Call",
    provider: "Exotel",
    status: "planned",
    sender: { displayName: "IVR Outbound", address: "+91-4470XXXXXX", verified: false },
    limits: { perMinute: 200, perHour: 8_000, perDay: 120_000, perMonth: 2_400_000 },
    usage: { dailySent: 0, dailyCap: 120_000, monthlySent: 0, monthlyCap: 2_400_000 },
    queueDepth: 0,
    retry: { policyId: "rp-voice", maxAttempts: 2, intervalSeconds: 120 },
    health: { score: 0, latencyMs: 0, successRate: 0, errorRate: 0, lastCheckedAt: iso(0), incidents24h: 0 },
    configuration: { voiceProfile: "hindi-female" },
    createdAt: iso(-2 * 24 * 60),
    updatedAt: iso(-2 * 24 * 60),
  },
];

const orgs = ["org-mohfw", "org-eci", "org-nhm", "org-aiims", "org-ngdma"];
const langs = ["Hindi", "English", "Tamil", "Telugu", "Bengali", "Marathi"];
const campaignNames = [
  "Polio Vaccination Drive · Bihar",
  "Voter Awareness · Karnataka 2026",
  "Cyclone Alert · Odisha Coast",
  "Ayushman Bharat Enrollment · UP",
  "Dengue Prevention · Chennai",
  "PMKVY Skill Enrollment · MP",
  "Air Quality Advisory · Delhi NCR",
  "Blood Donation Camp · AIIMS Delhi",
  "Scholarship Deadline · Telangana",
  "Public Distribution · Kerala",
];

const channelKinds: ChannelKind[] = ["email", "sms", "whatsapp", "push", "web_broadcast", "social_broadcast"];

const makeJob = (i: number, status: DeliveryStatus, scheduledOffset?: number): DeliveryJob => {
  const total = 5000 + i * 1200 + Math.floor(Math.random() * 8000);
  const delivered =
    status === "delivered" || status === "opened" || status === "clicked"
      ? Math.floor(total * (0.92 + Math.random() * 0.06))
      : status === "processing"
        ? Math.floor(total * 0.4)
        : status === "failed"
          ? Math.floor(total * 0.2)
          : 0;
  const failed = status === "failed" ? Math.floor(total * (0.1 + Math.random() * 0.15)) : Math.floor(total * 0.02);
  const opened = Math.floor(delivered * (0.35 + Math.random() * 0.25));
  const clicked = Math.floor(opened * (0.18 + Math.random() * 0.15));
  const responded = Math.floor(clicked * (0.12 + Math.random() * 0.1));
  return {
    id: `job-${1000 + i}`,
    campaignId: `cmp-${100 + (i % campaignNames.length)}`,
    campaignName: campaignNames[i % campaignNames.length]!,
    channel: channelKinds[i % channelKinds.length]!,
    status,
    priority: (["low", "normal", "normal", "high", "urgent"] as const)[i % 5]!,
    totalRecipients: total,
    delivered,
    failed,
    pending: Math.max(0, total - delivered - failed),
    opened,
    clicked,
    responded,
    scheduledAt: scheduledOffset != null ? iso(scheduledOffset) : undefined,
    startedAt: status !== "scheduled" && status !== "queued" ? iso(-60 - i * 5) : undefined,
    completedAt: status === "delivered" || status === "failed" ? iso(-i * 3) : undefined,
    language: langs[i % langs.length]!,
    organizationId: orgs[i % orgs.length]!,
    ownerId: "usr-001",
    attempts: status === "failed" ? 3 : status === "retrying" ? 2 : 1,
    maxAttempts: 3,
    createdAt: iso(-120 - i * 15),
    updatedAt: iso(-i * 5),
  };
};

export const mockDeliveryJobs: DeliveryJob[] = [
  ...Array.from({ length: 6 }, (_, i) => makeJob(i, "delivered")),
  ...Array.from({ length: 4 }, (_, i) => makeJob(i + 10, "processing")),
  ...Array.from({ length: 3 }, (_, i) => makeJob(i + 20, "queued")),
  ...Array.from({ length: 4 }, (_, i) => makeJob(i + 30, "scheduled", 60 * (i + 1) * 4)),
  ...Array.from({ length: 3 }, (_, i) => makeJob(i + 40, "failed")),
  ...Array.from({ length: 2 }, (_, i) => makeJob(i + 50, "retrying")),
  ...Array.from({ length: 2 }, (_, i) => makeJob(i + 60, "cancelled")),
];

const jobsByStatus = (statuses: DeliveryStatus[]) =>
  mockDeliveryJobs.filter((j) => statuses.includes(j.status));

export const mockQueueSnapshots: DeliveryQueueSnapshot[] = [
  { kind: "delivery", label: "Delivery queue", count: jobsByStatus(["queued"]).length, throughputPerMinute: 4210, oldestAgeSeconds: 42, jobs: jobsByStatus(["queued"]) },
  { kind: "scheduled", label: "Scheduled queue", count: jobsByStatus(["scheduled"]).length, throughputPerMinute: 0, oldestAgeSeconds: 0, jobs: jobsByStatus(["scheduled"]) },
  { kind: "retry", label: "Retry queue", count: jobsByStatus(["retrying"]).length, throughputPerMinute: 128, oldestAgeSeconds: 320, jobs: jobsByStatus(["retrying"]) },
  { kind: "failed", label: "Failed queue", count: jobsByStatus(["failed"]).length, throughputPerMinute: 0, oldestAgeSeconds: 1800, jobs: jobsByStatus(["failed"]) },
  { kind: "processing", label: "Processing queue", count: jobsByStatus(["processing"]).length, throughputPerMinute: 6120, oldestAgeSeconds: 90, jobs: jobsByStatus(["processing"]) },
  { kind: "cancelled", label: "Cancelled queue", count: jobsByStatus(["cancelled"]).length, throughputPerMinute: 0, oldestAgeSeconds: 0, jobs: jobsByStatus(["cancelled"]) },
  { kind: "completed", label: "Completed queue", count: jobsByStatus(["delivered"]).length, throughputPerMinute: 0, oldestAgeSeconds: 0, jobs: jobsByStatus(["delivered"]) },
];

const recipientNames = [
  "Rahul Sharma", "Priya Iyer", "Aditya Verma", "Meera Nair", "Rohan Das",
  "Anjali Menon", "Sanjay Reddy", "Kavya Patel", "Arjun Singh", "Sneha Kulkarni",
  "Farhan Khan", "Divya Rao", "Vikram Joshi", "Neha Gupta", "Ishaan Bhat",
];

export const mockRecipients: DeliveryRecipient[] = recipientNames.map((name, i) => {
  const status: DeliveryStatus = (
    ["delivered", "opened", "clicked", "responded", "delivered", "failed", "bounced", "delivered", "opened", "delivered", "clicked", "delivered", "responded", "failed", "delivered"] as DeliveryStatus[]
  )[i]!;
  return {
    id: `rcpt-${i + 1}`,
    contactId: `ctc-${i + 1}`,
    name,
    address: i % 2 === 0 ? `+91-98${(10000000 + i * 137).toString().slice(0, 8)}` : `${name.toLowerCase().replace(/\s/g, ".")}@mail.in`,
    language: langs[i % langs.length]!,
    channel: channelKinds[i % channelKinds.length]!,
    status,
    attempts: status === "failed" || status === "bounced" ? 3 : 1,
    lastAttemptAt: iso(-i * 12),
    deliveredAt: status !== "failed" && status !== "bounced" ? iso(-i * 12 - 4) : undefined,
    openedAt: ["opened", "clicked", "responded"].includes(status) ? iso(-i * 12 - 2) : undefined,
    clickedAt: ["clicked", "responded"].includes(status) ? iso(-i * 12 - 1) : undefined,
    respondedAt: status === "responded" ? iso(-i * 12) : undefined,
    failureCategory: status === "failed" ? "provider_error" : status === "bounced" ? "bounced" : undefined,
    failureReason: status === "failed" ? "Upstream provider 5xx" : status === "bounced" ? "Mailbox full" : undefined,
    device: i % 3 === 0 ? "Android" : i % 3 === 1 ? "iOS" : "Desktop",
  };
});

export const mockCommunicationOverview: CommunicationOverview = {
  kpis: {
    sent: 1_204_892,
    delivered: 1_182_004,
    failed: 22_888,
    queued: 8_244,
    scheduled: 12_310,
    openRate: 42.8,
    clickRate: 12.4,
    responseRate: 3.9,
    bounceRate: 1.9,
    deliverySuccessRate: 98.1,
  },
  deliveryTimeline: days(14).map((date, i) => ({
    date,
    value: 60_000 + Math.round(Math.sin(i / 2) * 12_000 + i * 800),
    secondary: 55_000 + Math.round(Math.sin(i / 2 + 0.4) * 11_000 + i * 700),
  })),
  channelDistribution: [
    { label: "SMS", value: 612_000 },
    { label: "WhatsApp", value: 284_000 },
    { label: "Email", value: 168_000 },
    { label: "Push", value: 108_000 },
    { label: "Web", value: 24_000 },
    { label: "Social", value: 8_000 },
  ],
  languageDistribution: langs.map((l, i) => ({ label: l, value: 220_000 - i * 26_000 })),
  dailyTrend: days(30).map((date, i) => ({ date, value: 40_000 + Math.round(Math.cos(i / 3) * 8_000 + i * 500) })),
  engagement: days(14).map((date, i) => ({
    date,
    value: 12 + Math.round(Math.sin(i / 2) * 4),
    secondary: 3 + Math.round(Math.cos(i / 2) * 1.5),
  })),
  failureBreakdown: [
    { category: "provider_error", label: "Provider error", count: 8_412, share: 36.8 },
    { category: "invalid_address", label: "Invalid address", count: 5_233, share: 22.9 },
    { category: "bounced", label: "Bounced", count: 3_942, share: 17.2 },
    { category: "rate_limited", label: "Rate limited", count: 2_204, share: 9.6 },
    { category: "unsubscribed", label: "Unsubscribed", count: 1_802, share: 7.9 },
    { category: "timeout", label: "Timeout", count: 1_295, share: 5.6 },
  ],
  recentDeliveries: jobsByStatus(["delivered"]).slice(0, 5),
  recentFailures: jobsByStatus(["failed"]).slice(0, 5),
  upcomingScheduled: jobsByStatus(["scheduled"]).slice(0, 5),
};

export const mockCommunicationTimeline: CommunicationTimelineEvent[] = [
  { id: "t1", step: "created", at: iso(-60 * 24 * 5), actor: "Meera Nair" },
  { id: "t2", step: "approved", at: iso(-60 * 24 * 4), actor: "Rahul Sharma" },
  { id: "t3", step: "scheduled", at: iso(-60 * 24 * 3), actor: "Automation" },
  { id: "t4", step: "sent", at: iso(-60 * 6), channel: "sms" },
  { id: "t5", step: "delivered", at: iso(-60 * 5), channel: "sms", status: "delivered" },
  { id: "t6", step: "opened", at: iso(-60 * 4), channel: "sms" },
  { id: "t7", step: "clicked", at: iso(-60 * 3), channel: "sms" },
  { id: "t8", step: "responded", at: iso(-60 * 2), channel: "sms" },
  { id: "t9", step: "completed", at: iso(-30), actor: "Automation" },
];

export const mockEngagementOverview: EngagementOverview = {
  metrics: {
    opens: 512_002,
    clicks: 148_204,
    replies: 46_820,
    shares: 12_402,
    downloads: 8_902,
    registrations: 22_104,
    attendance: 9_820,
    participation: 66.4,
    sentimentScore: 72,
  },
  heatmap: (() => {
    const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const cells: EngagementOverview["heatmap"] = [];
    for (const day of dayNames) for (let h = 0; h < 24; h++)
      cells.push({ day, hour: h, value: Math.floor(20 + Math.random() * 80 * (h > 7 && h < 21 ? 1.2 : 0.4)) });
    return cells;
  })(),
  trends: days(14).map((date, i) => ({
    date,
    opens: 32_000 + Math.round(Math.sin(i / 2) * 6_000),
    clicks: 9_000 + Math.round(Math.cos(i / 2) * 2_500),
    replies: 2_800 + Math.round(Math.sin(i / 3) * 900),
  })),
  channelComparison: [
    { label: "SMS", opens: 220_000, clicks: 68_000, replies: 22_000 },
    { label: "WhatsApp", opens: 172_000, clicks: 52_000, replies: 18_000 },
    { label: "Email", opens: 84_000, clicks: 21_000, replies: 4_600 },
    { label: "Push", opens: 30_000, clicks: 6_400, replies: 1_800 },
  ],
  languageComparison: langs.map((l, i) => ({
    label: l,
    opens: 90_000 - i * 12_000,
    clicks: 28_000 - i * 3_600,
    replies: 8_400 - i * 1_100,
  })),
  audienceComparison: [
    { label: "Rural households", opens: 190_000, clicks: 44_000, replies: 12_800 },
    { label: "Urban commuters", opens: 148_000, clicks: 52_000, replies: 14_200 },
    { label: "Healthcare workers", opens: 72_000, clicks: 28_000, replies: 9_400 },
    { label: "Students · 18–25", opens: 102_000, clicks: 24_000, replies: 10_400 },
  ],
};

export const mockSchedules: ScheduleConfig[] = [
  {
    id: "sch-1",
    campaignId: "cmp-101",
    campaignName: "Voter Awareness · Karnataka 2026",
    mode: "scheduled",
    timezone: "Asia/Kolkata",
    startAt: iso(60 * 6),
    estimatedWindow: { start: iso(60 * 6), end: iso(60 * 8) },
    createdAt: iso(-60 * 48),
    updatedAt: iso(-60 * 2),
  },
  {
    id: "sch-2",
    campaignId: "cmp-102",
    campaignName: "Weekly Immunization Reminder",
    mode: "recurring",
    timezone: "Asia/Kolkata",
    startAt: iso(60 * 24),
    recurrence: { pattern: "weekly", interval: 1, daysOfWeek: [1, 4] },
    estimatedWindow: { start: iso(60 * 24), end: iso(60 * 25) },
    createdAt: iso(-60 * 24 * 10),
    updatedAt: iso(-60),
  },
  {
    id: "sch-3",
    campaignId: "cmp-103",
    campaignName: "Monthly PDS Beneficiary Update",
    mode: "recurring",
    timezone: "Asia/Kolkata",
    startAt: iso(60 * 24 * 3),
    recurrence: { pattern: "monthly", interval: 1, dayOfMonth: 5 },
    createdAt: iso(-60 * 24 * 30),
    updatedAt: iso(-60 * 12),
  },
];

export const mockRetryPolicies: RetryPolicy[] = [
  {
    id: "rp-email", name: "Email standard", description: "Balanced retry for transactional email.",
    maxAttempts: 5, intervalSeconds: 60, backoff: "exponential", backoffMultiplier: 2, maxIntervalSeconds: 3600,
    channels: ["email"], retryOn: ["provider_error", "timeout", "rate_limited"], isDefault: true,
    createdAt: iso(-60 * 24 * 90), updatedAt: iso(-60 * 24 * 2),
  },
  {
    id: "rp-sms", name: "SMS aggressive", description: "Fast retry for time-sensitive alerts.",
    maxAttempts: 3, intervalSeconds: 30, backoff: "linear", backoffMultiplier: 1.5, maxIntervalSeconds: 900,
    channels: ["sms"], retryOn: ["provider_error", "timeout"], isDefault: true,
    createdAt: iso(-60 * 24 * 60), updatedAt: iso(-60 * 24),
  },
  {
    id: "rp-whatsapp", name: "WhatsApp default",
    maxAttempts: 4, intervalSeconds: 45, backoff: "exponential", backoffMultiplier: 2, maxIntervalSeconds: 1800,
    channels: ["whatsapp"], retryOn: ["provider_error", "rate_limited", "timeout"], isDefault: true,
    createdAt: iso(-60 * 24 * 45), updatedAt: iso(-60 * 24 * 3),
  },
  {
    id: "rp-push", name: "Push minimal",
    maxAttempts: 2, intervalSeconds: 15, backoff: "fixed", backoffMultiplier: 1, maxIntervalSeconds: 30,
    channels: ["push"], retryOn: ["provider_error"], isDefault: true,
    createdAt: iso(-60 * 24 * 30), updatedAt: iso(-60 * 24),
  },
  {
    id: "rp-web", name: "Web broadcast",
    maxAttempts: 1, intervalSeconds: 10, backoff: "fixed", backoffMultiplier: 1, maxIntervalSeconds: 10,
    channels: ["web_broadcast"], retryOn: ["provider_error"], isDefault: true,
    createdAt: iso(-60 * 24 * 20), updatedAt: iso(-60 * 24),
  },
  {
    id: "rp-social", name: "Social broadcast",
    maxAttempts: 3, intervalSeconds: 90, backoff: "exponential", backoffMultiplier: 2, maxIntervalSeconds: 1800,
    channels: ["social_broadcast"], retryOn: ["provider_error", "rate_limited"], isDefault: true,
    createdAt: iso(-60 * 24 * 15), updatedAt: iso(-60 * 24),
  },
  {
    id: "rp-voice", name: "Voice default",
    maxAttempts: 2, intervalSeconds: 120, backoff: "linear", backoffMultiplier: 1, maxIntervalSeconds: 240,
    channels: ["voice"], retryOn: ["provider_error", "timeout"], isDefault: true,
    createdAt: iso(-60 * 24 * 2), updatedAt: iso(-60 * 24 * 2),
  },
];

export const mockEngagementReports: EngagementReport[] = [
  { id: "er-1", name: "Q4 Channel performance", scope: "channel", createdAt: iso(-60 * 24 * 8), createdBy: "Priya Iyer", filters: {} },
  { id: "er-2", name: "Hindi vs Tamil open rates", scope: "language", createdAt: iso(-60 * 24 * 3), createdBy: "Rahul Sharma", filters: {} },
  { id: "er-3", name: "MoHFW campaign summary", scope: "campaign", createdAt: iso(-60 * 24 * 2), createdBy: "Meera Nair", filters: {} },
];

export const mockPreferences: NotificationPreferences = {
  userId: "usr-001",
  email: { enabled: true, digest: "daily", quietHours: { start: "22:00", end: "07:00", enabled: true } },
  sms: { enabled: true, digest: "off", quietHours: { start: "22:00", end: "07:00", enabled: true } },
  push: { enabled: true, digest: "off", quietHours: { start: "23:00", end: "06:00", enabled: false } },
  inApp: { enabled: true, digest: "off", quietHours: { start: "00:00", end: "00:00", enabled: false } },
  emergencyOverride: true,
  language: "English",
  updatedAt: iso(-60 * 24),
};
