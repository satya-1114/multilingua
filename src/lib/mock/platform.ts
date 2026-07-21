import type { Workspace } from "@/types/workspace";
import type { ExecutiveOverview, SavedReport, ReportResult, ReportKind } from "@/types/analytics";
import type { Workflow, WorkflowTemplate } from "@/types/automation";
import type { Integration, Webhook, WebhookDelivery } from "@/types/integration";
import type { ServiceStatus, QueueSnapshot, HealthMetric, LogEntry } from "@/types/monitoring";
import type { FeatureFlag, ReleaseNote, LicenseInfo, PlatformConfigSection } from "@/types/system";
import type { ActiveSession, LoginEvent, SecurityAlert, PasswordPolicy } from "@/types/security";
import type { KnowledgeArticle, Faq, KeyboardShortcut } from "@/types/help";

const now = new Date();
const iso = (daysAgo: number, hours = 0) =>
  new Date(now.getTime() - daysAgo * 86400000 - hours * 3600000).toISOString();

export const mockWorkspaces: Workspace[] = [
  {
    id: "ws-01",
    tenantId: "tenant-national-hm",
    name: "Ministry of Health & Family Welfare",
    slug: "mohfw",
    colorAccent: "#2563EB",
    organizationType: "Government",
    plan: "enterprise",
    region: "IN-DL",
    timezone: "Asia/Kolkata",
    languages: ["en", "hi", "ta", "te", "bn", "mr"],
    primaryLanguage: "hi",
    storageQuotaGb: 500,
    storageUsedGb: 214.6,
    apiQuotaMonthly: 5_000_000,
    apiUsedThisMonth: 2_140_882,
    memberCount: 184,
    isDefault: true,
    isFavorite: true,
    lastAccessedAt: iso(0, 1),
    createdAt: iso(720),
  },
  {
    id: "ws-02",
    tenantId: "tenant-aiims-delhi",
    name: "AIIMS Delhi Communications",
    slug: "aiims-delhi",
    colorAccent: "#0EA5E9",
    organizationType: "Healthcare",
    plan: "enterprise",
    region: "IN-DL",
    timezone: "Asia/Kolkata",
    languages: ["en", "hi"],
    primaryLanguage: "en",
    storageQuotaGb: 200,
    storageUsedGb: 94.2,
    apiQuotaMonthly: 1_000_000,
    apiUsedThisMonth: 412_310,
    memberCount: 62,
    isFavorite: true,
    lastAccessedAt: iso(1),
    createdAt: iso(540),
  },
  {
    id: "ws-03",
    tenantId: "tenant-tn-education",
    name: "Tamil Nadu School Education",
    slug: "tn-education",
    colorAccent: "#8B5CF6",
    organizationType: "Education",
    plan: "growth",
    region: "IN-TN",
    timezone: "Asia/Kolkata",
    languages: ["en", "ta"],
    primaryLanguage: "ta",
    storageQuotaGb: 100,
    storageUsedGb: 41.8,
    apiQuotaMonthly: 500_000,
    apiUsedThisMonth: 189_112,
    memberCount: 41,
    lastAccessedAt: iso(3),
    createdAt: iso(380),
  },
  {
    id: "ws-04",
    tenantId: "tenant-goonj",
    name: "Goonj Foundation",
    slug: "goonj",
    colorAccent: "#22C55E",
    organizationType: "NGO / Non-profit",
    plan: "growth",
    region: "IN-DL",
    timezone: "Asia/Kolkata",
    languages: ["en", "hi", "mr"],
    primaryLanguage: "hi",
    storageQuotaGb: 50,
    storageUsedGb: 22.4,
    apiQuotaMonthly: 250_000,
    apiUsedThisMonth: 88_402,
    memberCount: 24,
    lastAccessedAt: iso(6),
    createdAt: iso(210),
  },
  {
    id: "ws-05",
    tenantId: "tenant-pune-collectorate",
    name: "Pune District Collectorate",
    slug: "pune-collectorate",
    colorAccent: "#F59E0B",
    organizationType: "Government",
    plan: "enterprise",
    region: "IN-MH",
    timezone: "Asia/Kolkata",
    languages: ["en", "mr", "hi"],
    primaryLanguage: "mr",
    storageQuotaGb: 250,
    storageUsedGb: 130.9,
    apiQuotaMonthly: 2_000_000,
    apiUsedThisMonth: 941_003,
    memberCount: 97,
    lastAccessedAt: iso(2),
    createdAt: iso(430),
  },
];

// --- Analytics ---

const days = (n: number, factor = 1, jitter = 0.15) =>
  Array.from({ length: n }, (_, i) => {
    const d = new Date(now.getTime() - (n - 1 - i) * 86400000);
    return {
      date: d.toISOString().slice(0, 10),
      value: Math.round(factor * (1 + Math.sin(i / 2.4) * jitter) + i * factor * 0.05),
    };
  });

export const mockExecutive: ExecutiveOverview = {
  kpis: [
    { label: "Total reach", value: 12_480_311, delta: 8.4, helper: "vs prev 30d" },
    { label: "Active audiences", value: 842_190, delta: 3.1, helper: "across 12 states" },
    { label: "Campaigns live", value: 47, delta: -2.0, helper: "7 pending approval" },
    { label: "Avg engagement", value: 41, delta: 4.7, helper: "%" },
  ],
  reach: days(30, 380_000).map((d, i) => ({
    date: d.date,
    delivered: d.value,
    engaged: Math.round(d.value * 0.42 + i * 1200),
  })),
  audienceGrowth: days(12, 12_000).map((d) => ({
    date: d.date,
    total: d.value,
    verified: Math.round(d.value * 0.7),
  })),
  languages: [
    { label: "Hindi", value: 42 },
    { label: "English", value: 21 },
    { label: "Tamil", value: 12 },
    { label: "Telugu", value: 9 },
    { label: "Marathi", value: 8 },
    { label: "Bengali", value: 8 },
  ],
  organizations: [
    { label: "Government", value: 48 },
    { label: "Healthcare", value: 21 },
    { label: "Education", value: 14 },
    { label: "NGO", value: 11 },
    { label: "Enterprise", value: 6 },
  ],
  engagement: days(14, 100).map((d) => ({
    date: d.date,
    open: d.value + 20,
    click: Math.round(d.value * 0.4),
    reply: Math.round(d.value * 0.12),
  })),
  delivery: days(14, 200).map((d) => ({
    date: d.date,
    sms: Math.round(d.value * 1.6),
    email: Math.round(d.value * 1.2),
    whatsapp: Math.round(d.value * 0.9),
    push: Math.round(d.value * 0.5),
  })),
  activity: days(14, 40).map((d) => ({
    date: d.date,
    logins: d.value + 10,
    actions: Math.round(d.value * 3.2),
  })),
  approvals: [
    { label: "Awaiting review", value: 12 },
    { label: "Approved this week", value: 34 },
    { label: "Avg turnaround (hrs)", value: 4 },
    { label: "Rejection rate", value: 6, helper: "%" },
  ],
};

export const mockReports: SavedReport[] = [
  {
    id: "rep-01",
    name: "Weekly campaign performance",
    kind: "campaign",
    description: "Delivery, engagement and reach split by language.",
    createdBy: "Ananya Rao",
    createdAt: iso(45),
    lastRunAt: iso(1),
    filters: { period: "last_7d" },
    scheduled: true,
  },
  {
    id: "rep-02",
    name: "Audience growth by district",
    kind: "audience",
    description: "Verified vs opted-in contacts across districts.",
    createdBy: "Rahul Menon",
    createdAt: iso(90),
    lastRunAt: iso(3),
    filters: { state: "Tamil Nadu" },
  },
  {
    id: "rep-03",
    name: "AI translation usage",
    kind: "translation",
    description: "Language pairs, tokens consumed, quality scores.",
    createdBy: "Priya Iyer",
    createdAt: iso(21),
    filters: {},
  },
  {
    id: "rep-04",
    name: "Security audit — Q4",
    kind: "security",
    description: "Login failures, permission changes, blocked users.",
    createdBy: "Vikram Shetty",
    createdAt: iso(14),
    lastRunAt: iso(2),
    filters: {},
  },
];

export function buildReportResult(kind: ReportKind): ReportResult {
  const columnsMap: Record<ReportKind, ReportResult["columns"]> = {
    campaign: [
      { key: "campaign", label: "Campaign", kind: "text" },
      { key: "language", label: "Language", kind: "text" },
      { key: "reach", label: "Reach", kind: "number" },
      { key: "engaged", label: "Engaged", kind: "number" },
      { key: "delivered", label: "Delivered %", kind: "number" },
    ],
    audience: [
      { key: "district", label: "District", kind: "text" },
      { key: "state", label: "State", kind: "text" },
      { key: "total", label: "Total", kind: "number" },
      { key: "verified", label: "Verified", kind: "number" },
    ],
    organization: [
      { key: "organization", label: "Organization", kind: "text" },
      { key: "type", label: "Type", kind: "text" },
      { key: "campaigns", label: "Campaigns", kind: "number" },
      { key: "reach", label: "Reach", kind: "number" },
    ],
    delivery: [
      { key: "channel", label: "Channel", kind: "text" },
      { key: "sent", label: "Sent", kind: "number" },
      { key: "delivered", label: "Delivered", kind: "number" },
      { key: "failed", label: "Failed", kind: "number" },
    ],
    template: [
      { key: "template", label: "Template", kind: "text" },
      { key: "channel", label: "Channel", kind: "text" },
      { key: "used", label: "Used", kind: "number" },
    ],
    translation: [
      { key: "pair", label: "Language pair", kind: "text" },
      { key: "requests", label: "Requests", kind: "number" },
      { key: "tokens", label: "Tokens", kind: "number" },
    ],
    ai: [
      { key: "prompt", label: "Prompt", kind: "text" },
      { key: "runs", label: "Runs", kind: "number" },
      { key: "tokens", label: "Tokens", kind: "number" },
    ],
    audit: [
      { key: "actor", label: "Actor", kind: "text" },
      { key: "action", label: "Action", kind: "text" },
      { key: "entity", label: "Entity", kind: "text" },
      { key: "at", label: "At", kind: "date" },
    ],
    security: [
      { key: "actor", label: "Actor", kind: "text" },
      { key: "event", label: "Event", kind: "text" },
      { key: "ip", label: "IP", kind: "text" },
      { key: "status", label: "Status", kind: "text" },
    ],
    activity: [
      { key: "actor", label: "Actor", kind: "text" },
      { key: "actions", label: "Actions", kind: "number" },
      { key: "lastAt", label: "Last at", kind: "date" },
    ],
  };
  const columns = columnsMap[kind];
  const rows = Array.from({ length: 18 }).map((_, i) => {
    const row: Record<string, string | number> = { id: String(i + 1) };
    columns.forEach((c) => {
      if (c.kind === "number") row[c.key] = Math.round(1000 + Math.random() * 90000);
      else if (c.kind === "date") row[c.key] = iso(i, 2);
      else row[c.key] = `${c.label} ${i + 1}`;
    });
    return row as ReportResult["rows"][number];
  });
  return { columns, rows, total: rows.length };
}

// --- Automation ---

export const mockWorkflowTemplates: WorkflowTemplate[] = [
  {
    id: "tpl-camp-approval",
    name: "Campaign approval",
    category: "Governance",
    description: "Draft → Reviewer → Approver → Launch",
    nodes: [
      { id: "n1", kind: "trigger", title: "Campaign submitted", x: 40, y: 80 },
      { id: "n2", kind: "approval", title: "Content review", x: 240, y: 80 },
      { id: "n3", kind: "approval", title: "Compliance approval", x: 440, y: 80 },
      { id: "n4", kind: "communication", title: "Launch to audience", x: 640, y: 80 },
      { id: "n5", kind: "end", title: "Completed", x: 840, y: 80 },
    ],
    edges: [
      { id: "e1", from: "n1", to: "n2" },
      { id: "e2", from: "n2", to: "n3" },
      { id: "e3", from: "n3", to: "n4" },
      { id: "e4", from: "n4", to: "n5" },
    ],
  },
  {
    id: "tpl-emergency",
    name: "Emergency alert",
    category: "Public safety",
    description: "Trigger → AI localize → Multi-channel broadcast",
    nodes: [
      { id: "n1", kind: "trigger", title: "Incident reported", x: 40, y: 80 },
      { id: "n2", kind: "ai", title: "AI localization", x: 240, y: 80 },
      { id: "n3", kind: "audience", title: "Affected districts", x: 440, y: 80 },
      { id: "n4", kind: "communication", title: "SMS + Push + WhatsApp", x: 640, y: 80 },
      { id: "n5", kind: "end", title: "Broadcast complete", x: 840, y: 80 },
    ],
    edges: [
      { id: "e1", from: "n1", to: "n2" },
      { id: "e2", from: "n2", to: "n3" },
      { id: "e3", from: "n3", to: "n4" },
      { id: "e4", from: "n4", to: "n5" },
    ],
  },
  {
    id: "tpl-healthcare",
    name: "Healthcare notice",
    category: "Healthcare",
    description: "Screening reminder for at-risk cohorts",
    nodes: [
      { id: "n1", kind: "trigger", title: "Weekly schedule", x: 40, y: 80 },
      { id: "n2", kind: "audience", title: "At-risk cohort", x: 240, y: 80 },
      { id: "n3", kind: "template", title: "Screening notice", x: 440, y: 80 },
      { id: "n4", kind: "communication", title: "SMS", x: 640, y: 80 },
      { id: "n5", kind: "end", title: "Done", x: 840, y: 80 },
    ],
    edges: [
      { id: "e1", from: "n1", to: "n2" },
      { id: "e2", from: "n2", to: "n3" },
      { id: "e3", from: "n3", to: "n4" },
      { id: "e4", from: "n4", to: "n5" },
    ],
  },
  {
    id: "tpl-university",
    name: "University circular",
    category: "Education",
    description: "Approver-gated circular to registered students",
    nodes: [
      { id: "n1", kind: "trigger", title: "Manual start", x: 40, y: 80 },
      { id: "n2", kind: "approval", title: "Dean approval", x: 240, y: 80 },
      { id: "n3", kind: "audience", title: "Enrolled students", x: 440, y: 80 },
      { id: "n4", kind: "communication", title: "Email + Push", x: 640, y: 80 },
      { id: "n5", kind: "end", title: "Circular sent", x: 840, y: 80 },
    ],
    edges: [
      { id: "e1", from: "n1", to: "n2" },
      { id: "e2", from: "n2", to: "n3" },
      { id: "e3", from: "n3", to: "n4" },
      { id: "e4", from: "n4", to: "n5" },
    ],
  },
  {
    id: "tpl-ngo",
    name: "NGO campaign",
    category: "NGO",
    description: "Donor + beneficiary awareness sequence",
    nodes: [
      { id: "n1", kind: "trigger", title: "Campaign start", x: 40, y: 80 },
      { id: "n2", kind: "template", title: "Awareness content", x: 240, y: 80 },
      { id: "n3", kind: "delay", title: "Wait 2 days", x: 440, y: 80 },
      { id: "n4", kind: "communication", title: "WhatsApp + Email", x: 640, y: 80 },
      { id: "n5", kind: "end", title: "Done", x: 840, y: 80 },
    ],
    edges: [
      { id: "e1", from: "n1", to: "n2" },
      { id: "e2", from: "n2", to: "n3" },
      { id: "e3", from: "n3", to: "n4" },
      { id: "e4", from: "n4", to: "n5" },
    ],
  },
  {
    id: "tpl-corporate",
    name: "Corporate announcement",
    category: "Enterprise",
    description: "Region-based rollout of company announcements",
    nodes: [
      { id: "n1", kind: "trigger", title: "Announcement created", x: 40, y: 80 },
      { id: "n2", kind: "condition", title: "Region check", x: 240, y: 80 },
      { id: "n3", kind: "template", title: "Localized copy", x: 440, y: 80 },
      { id: "n4", kind: "communication", title: "Email + Slack", x: 640, y: 80 },
      { id: "n5", kind: "end", title: "Delivered", x: 840, y: 80 },
    ],
    edges: [
      { id: "e1", from: "n1", to: "n2" },
      { id: "e2", from: "n2", to: "n3" },
      { id: "e3", from: "n3", to: "n4" },
      { id: "e4", from: "n4", to: "n5" },
    ],
  },
];

export const mockWorkflows: Workflow[] = [
  {
    id: "wf-01",
    name: "National dengue awareness pipeline",
    description: "Multi-language delivery, dean-approved, weekly cadence.",
    status: "published",
    version: 4,
    category: "Healthcare",
    nodes: mockWorkflowTemplates[2].nodes,
    edges: mockWorkflowTemplates[2].edges,
    updatedAt: iso(1),
    updatedBy: "Dr. Kavita Menon",
    createdAt: iso(80),
    runsThisMonth: 128,
  },
  {
    id: "wf-02",
    name: "Cyclone emergency broadcast",
    description: "IMD-triggered, coastal districts, high priority.",
    status: "published",
    version: 6,
    category: "Public safety",
    nodes: mockWorkflowTemplates[1].nodes,
    edges: mockWorkflowTemplates[1].edges,
    updatedAt: iso(3),
    updatedBy: "Vikram Shetty",
    createdAt: iso(140),
    runsThisMonth: 12,
  },
  {
    id: "wf-03",
    name: "TN school exam circulars",
    description: "Term-based, district-scoped, Tamil primary.",
    status: "draft",
    version: 1,
    category: "Education",
    nodes: mockWorkflowTemplates[3].nodes,
    edges: mockWorkflowTemplates[3].edges,
    updatedAt: iso(6),
    updatedBy: "Ananya Rao",
    createdAt: iso(10),
    runsThisMonth: 0,
  },
];

// --- Integrations ---

export const mockIntegrations: Integration[] = [
  { id: "int-smtp", provider: "Corporate SMTP", category: "email", description: "Internal SMTP relay for transactional email.", status: "connected", logoInitials: "SM", color: "#2563EB", lastSyncAt: iso(0, 2), requestsThisMonth: 412_881, errorRate: 0.4, environment: "production", authType: "smtp" },
  { id: "int-sendgrid", provider: "SendGrid", category: "email", description: "High-volume transactional email delivery.", status: "connected", logoInitials: "SG", color: "#1D4ED8", lastSyncAt: iso(0, 1), requestsThisMonth: 224_098, errorRate: 0.9, environment: "production", authType: "api_key" },
  { id: "int-mailgun", provider: "Mailgun", category: "email", description: "Backup delivery route with EU region.", status: "disconnected", logoInitials: "MG", color: "#DC2626", requestsThisMonth: 0, errorRate: 0, environment: "production", authType: "api_key" },
  { id: "int-ses", provider: "Amazon SES", category: "email", description: "Regional email delivery for scale.", status: "pending", logoInitials: "SE", color: "#F59E0B", requestsThisMonth: 0, errorRate: 0, environment: "staging", authType: "api_key" },
  { id: "int-twilio", provider: "Twilio", category: "sms", description: "SMS delivery to Indian numbers.", status: "connected", logoInitials: "TW", color: "#DC2626", lastSyncAt: iso(0), requestsThisMonth: 984_411, errorRate: 1.2, environment: "production", authType: "api_key" },
  { id: "int-msg91", provider: "MSG91", category: "sms", description: "Domestic SMS with DLT compliance.", status: "connected", logoInitials: "M9", color: "#2563EB", lastSyncAt: iso(0, 4), requestsThisMonth: 612_401, errorRate: 0.7, environment: "production", authType: "api_key" },
  { id: "int-textlocal", provider: "Textlocal", category: "sms", description: "Bulk SMS for awareness campaigns.", status: "disconnected", logoInitials: "TL", color: "#8B5CF6", requestsThisMonth: 0, errorRate: 0, environment: "production", authType: "api_key" },
  { id: "int-meta", provider: "Meta WhatsApp Business", category: "whatsapp", description: "Official WhatsApp Business Platform.", status: "connected", logoInitials: "WA", color: "#22C55E", lastSyncAt: iso(0), requestsThisMonth: 511_223, errorRate: 0.3, environment: "production", authType: "oauth" },
  { id: "int-gupshup", provider: "Gupshup", category: "whatsapp", description: "Conversation APIs with campaign templates.", status: "pending", logoInitials: "GS", color: "#0EA5E9", requestsThisMonth: 0, errorRate: 0, environment: "staging", authType: "api_key" },
  { id: "int-fcm", provider: "Firebase Cloud Messaging", category: "push", description: "Push to Android + Web clients.", status: "connected", logoInitials: "FB", color: "#F59E0B", lastSyncAt: iso(0, 6), requestsThisMonth: 288_412, errorRate: 0.2, environment: "production", authType: "api_key" },
  { id: "int-onesignal", provider: "OneSignal", category: "push", description: "Cross-platform push infrastructure.", status: "disconnected", logoInitials: "OS", color: "#DC2626", requestsThisMonth: 0, errorRate: 0, environment: "production", authType: "api_key" },
  { id: "int-fb", provider: "Facebook Pages", category: "social", description: "Publish awareness posts to official page.", status: "connected", logoInitials: "FB", color: "#2563EB", lastSyncAt: iso(1), requestsThisMonth: 1_204, errorRate: 0, environment: "production", authType: "oauth" },
  { id: "int-li", provider: "LinkedIn Org", category: "social", description: "Company page announcements.", status: "pending", logoInitials: "LI", color: "#0369A1", requestsThisMonth: 0, errorRate: 0, environment: "production", authType: "oauth" },
  { id: "int-x", provider: "X", category: "social", description: "Broadcast alerts to followers.", status: "disconnected", logoInitials: "X", color: "#0F172A", requestsThisMonth: 0, errorRate: 0, environment: "production", authType: "oauth" },
  { id: "int-tg", provider: "Telegram", category: "social", description: "Channel broadcast for districts.", status: "connected", logoInitials: "TG", color: "#0EA5E9", lastSyncAt: iso(2), requestsThisMonth: 8_412, errorRate: 0.1, environment: "production", authType: "bearer" },
  { id: "int-rest", provider: "REST API — Public Data", category: "api", description: "Pull cohorts from Aadhaar-linked services.", status: "error", logoInitials: "AP", color: "#DC2626", lastSyncAt: iso(0, 12), requestsThisMonth: 91_003, errorRate: 4.8, environment: "production", authType: "bearer" },
];

export const mockWebhooks: Webhook[] = [
  { id: "wh-01", name: "Campaign delivered", direction: "outgoing", url: "https://analytics.dept.gov.in/hooks/delivered", event: "campaign.delivered", secretMasked: "whsec_••••D8f2", active: true, successCount: 12482, failureCount: 12, lastDeliveryAt: iso(0) },
  { id: "wh-02", name: "SMS DLR", direction: "incoming", url: "/hooks/inbound/sms/dlr", event: "sms.delivery_report", secretMasked: "whsec_••••A31C", active: true, successCount: 981210, failureCount: 3421, lastDeliveryAt: iso(0) },
  { id: "wh-03", name: "External CRM sync", direction: "outgoing", url: "https://crm.example.org/api/sync", event: "audience.updated", secretMasked: "whsec_••••7F92", active: false, successCount: 4211, failureCount: 88, lastDeliveryAt: iso(2) },
];

export const mockWebhookDeliveries: WebhookDelivery[] = Array.from({ length: 18 }).map((_, i) => ({
  id: `whd-${i}`,
  webhookId: i % 3 === 0 ? "wh-01" : i % 3 === 1 ? "wh-02" : "wh-03",
  status: i % 7 === 0 ? "failed" : i % 11 === 0 ? "retrying" : "success",
  responseCode: i % 7 === 0 ? 500 : 200,
  attempt: i % 7 === 0 ? 3 : 1,
  at: iso(0, i),
  latencyMs: 80 + Math.round(Math.random() * 300),
}));

// --- Monitoring ---

export const mockServices: ServiceStatus[] = [
  { id: "svc-api", name: "Public API", status: "operational", latencyMs: 82, uptimePercent: 99.98, region: "ap-south-1" },
  { id: "svc-workers", name: "Background workers", status: "operational", latencyMs: 145, uptimePercent: 99.94, region: "ap-south-1" },
  { id: "svc-ai", name: "AI gateway", status: "degraded", latencyMs: 612, uptimePercent: 99.62, region: "ap-south-1" },
  { id: "svc-db", name: "Primary database", status: "operational", latencyMs: 9, uptimePercent: 99.99, region: "ap-south-1" },
  { id: "svc-sms", name: "SMS delivery", status: "operational", latencyMs: 210, uptimePercent: 99.90, region: "ap-south-1" },
  { id: "svc-storage", name: "Object storage", status: "operational", latencyMs: 41, uptimePercent: 99.99, region: "ap-south-1" },
];

export const mockQueues: QueueSnapshot[] = [
  { name: "Upload queue", pending: 12, running: 4, completed24h: 1841, failed24h: 6 },
  { name: "Translation queue", pending: 41, running: 8, completed24h: 6120, failed24h: 22 },
  { name: "AI queue", pending: 8, running: 3, completed24h: 981, failed24h: 4 },
  { name: "Delivery queue", pending: 214, running: 18, completed24h: 128_411, failed24h: 132 },
  { name: "Approval queue", pending: 12, running: 0, completed24h: 34, failed24h: 0 },
];

export const mockHealth: HealthMetric[] = [
  { id: "cpu", label: "CPU", value: 42, unit: "%", threshold: 80, status: "healthy" },
  { id: "mem", label: "Memory", value: 68, unit: "%", threshold: 85, status: "healthy" },
  { id: "storage", label: "Storage", value: 61, unit: "%", threshold: 90, status: "healthy" },
  { id: "db", label: "DB connections", value: 74, unit: "%", threshold: 90, status: "warning" },
  { id: "queue", label: "Queue lag", value: 3, unit: "s", threshold: 30, status: "healthy" },
  { id: "api", label: "API error rate", value: 0.4, unit: "%", threshold: 2, status: "healthy" },
];

const logMessages = [
  "Campaign launched",
  "Translation completed",
  "SMS batch dispatched",
  "AI generation completed",
  "Webhook delivered",
  "User signed in",
  "Approval granted",
  "Rate limit warning",
  "Provider retry",
  "Audience imported",
];
const logServices = ["campaign", "translation", "delivery", "ai", "webhook", "auth", "approval", "gateway", "integration", "audience"];
const logActors = ["ananya.rao", "rahul.menon", "priya.iyer", "vikram.shetty", "system", "kavita.menon"];

export const mockLogs: LogEntry[] = Array.from({ length: 60 }).map((_, i) => ({
  id: `log-${i}`,
  at: iso(0, i * 0.4),
  level: (["info", "info", "info", "warning", "error", "debug"] as const)[i % 6],
  service: logServices[i % logServices.length],
  message: logMessages[i % logMessages.length],
  actor: logActors[i % logActors.length],
  requestId: `req_${(1_000_000 + i).toString(36)}`,
}));

// --- System / admin ---

export const mockFeatureFlags: FeatureFlag[] = [
  { key: "ai_v2_editor", name: "AI editor v2", description: "New rich-text AI editing surface.", enabled: true, scope: "global", rolloutPercent: 100, updatedAt: iso(2), updatedBy: "System" },
  { key: "workflow_builder", name: "Workflow builder", description: "Visual automation designer.", enabled: true, scope: "workspace", rolloutPercent: 100, updatedAt: iso(1), updatedBy: "Vikram Shetty" },
  { key: "beta_analytics", name: "Beta analytics widgets", description: "Preview experimental dashboard cards.", enabled: false, scope: "workspace", rolloutPercent: 20, updatedAt: iso(5), updatedBy: "Priya Iyer" },
  { key: "webhooks_v2", name: "Webhooks v2", description: "Signed retries + delivery replays.", enabled: true, scope: "global", rolloutPercent: 60, updatedAt: iso(9), updatedBy: "System" },
  { key: "regional_ai", name: "Regional-language AI", description: "Preview additional Indic language models.", enabled: false, scope: "environment", rolloutPercent: 10, updatedAt: iso(14), updatedBy: "System" },
];

export const mockReleaseNotes: ReleaseNote[] = [
  { version: "5.2.0", date: iso(3), title: "Workflow automation + monitoring center", highlights: ["Visual workflow builder", "Ops monitoring dashboard", "Security center v1"] },
  { version: "5.1.4", date: iso(21), title: "Performance & accessibility", highlights: ["Faster list virtualization", "WCAG audit fixes", "Report exports"] },
  { version: "5.1.0", date: iso(45), title: "Analytics center", highlights: ["Executive dashboard", "Report builder", "Scheduled exports"] },
];

export const mockLicense: LicenseInfo = {
  plan: "Enterprise",
  seats: 250,
  seatsUsed: 184,
  renewsOn: new Date(now.getFullYear() + 1, 3, 1).toISOString(),
  contractId: "ENT-2026-IN-00841",
  features: ["Unlimited workspaces", "Advanced analytics", "SSO + SAML", "Custom retention", "Priority support"],
};

export const mockPlatformConfig: PlatformConfigSection[] = [
  {
    id: "email",
    label: "Email",
    description: "Delivery routing, from-address and DKIM.",
    entries: [
      { key: "email.default_provider", label: "Default provider", value: "sendgrid", kind: "select", options: ["sendgrid", "smtp", "mailgun", "ses"] },
      { key: "email.from_address", label: "From address", value: "no-reply@platform.gov.in", kind: "text" },
      { key: "email.dkim", label: "DKIM signing", value: true, kind: "boolean" },
    ],
  },
  {
    id: "sms",
    label: "SMS",
    description: "DLT-approved templates and default sender IDs.",
    entries: [
      { key: "sms.default_provider", label: "Default provider", value: "msg91", kind: "select", options: ["msg91", "twilio", "textlocal"] },
      { key: "sms.sender_id", label: "Sender ID", value: "GOVMLT", kind: "text" },
      { key: "sms.enforce_dlt", label: "Enforce DLT compliance", value: true, kind: "boolean" },
    ],
  },
  {
    id: "whatsapp",
    label: "WhatsApp",
    description: "Business account and template scope.",
    entries: [
      { key: "whatsapp.provider", label: "Provider", value: "meta", kind: "select", options: ["meta", "gupshup"] },
      { key: "whatsapp.template_language", label: "Default template locale", value: "hi_IN", kind: "text" },
    ],
  },
  {
    id: "push",
    label: "Push notifications",
    description: "Mobile and web push behavior.",
    entries: [
      { key: "push.provider", label: "Provider", value: "fcm", kind: "select", options: ["fcm", "onesignal"] },
      { key: "push.silent_hours", label: "Silent hours (start)", value: "22:00", kind: "text" },
    ],
  },
  {
    id: "storage",
    label: "Storage",
    description: "Media library quotas and retention.",
    entries: [
      { key: "storage.max_upload_mb", label: "Max upload (MB)", value: 100, kind: "number" },
      { key: "storage.retention_days", label: "Retention (days)", value: 365, kind: "number" },
    ],
  },
  {
    id: "auth",
    label: "Authentication",
    description: "Session and password policy.",
    entries: [
      { key: "auth.session_hours", label: "Session lifetime (hours)", value: 12, kind: "number" },
      { key: "auth.require_2fa", label: "Require 2FA for admins", value: true, kind: "boolean" },
      { key: "auth.password_min_length", label: "Password min length", value: 12, kind: "number" },
    ],
  },
  {
    id: "rate",
    label: "Rate limits",
    description: "Per-workspace throughput ceilings.",
    entries: [
      { key: "rate.api_per_min", label: "API req/min", value: 1200, kind: "number" },
      { key: "rate.campaigns_per_hour", label: "Campaign launches/hour", value: 40, kind: "number" },
    ],
  },
];

// --- Security ---

export const mockSessions: ActiveSession[] = [
  { id: "s1", device: "MacBook Pro", browser: "Chrome 128", ip: "103.42.11.9", location: "Delhi, IN", createdAt: iso(0, 6), lastActiveAt: iso(0), current: true },
  { id: "s2", device: "iPhone 15", browser: "Safari", ip: "49.207.11.24", location: "Chennai, IN", createdAt: iso(1), lastActiveAt: iso(0, 4) },
  { id: "s3", device: "Windows Workstation", browser: "Edge 128", ip: "115.240.4.11", location: "Pune, IN", createdAt: iso(3), lastActiveAt: iso(1) },
];

export const mockLogins: LoginEvent[] = Array.from({ length: 22 }).map((_, i) => ({
  id: `l-${i}`,
  at: iso(0, i * 2),
  actor: logActors[i % logActors.length] + "@dept.gov.in",
  ip: `10${i % 9}.${20 + i}.${i * 3}.${i + 4}`,
  status: i % 6 === 0 ? "failed" : i % 17 === 0 ? "blocked" : "success",
  method: i % 4 === 0 ? "sso" : "password",
  location: ["Delhi, IN", "Chennai, IN", "Mumbai, IN", "Bengaluru, IN"][i % 4],
}));

export const mockAlerts: SecurityAlert[] = [
  { id: "a1", severity: "high", title: "Unusual login from new region", description: "3 failed sign-ins from Bengaluru for user rahul.menon.", at: iso(0, 3), status: "open" },
  { id: "a2", severity: "medium", title: "API rate limit hit", description: "Public API rate limit reached on integration Meta WhatsApp.", at: iso(1), status: "acknowledged" },
  { id: "a3", severity: "low", title: "Password expiring", description: "12 users have passwords expiring in the next 7 days.", at: iso(2), status: "open" },
  { id: "a4", severity: "critical", title: "Webhook signing key rotated", description: "External CRM webhook rejected 8 deliveries after rotation.", at: iso(0, 10), status: "resolved" },
];

export const defaultPasswordPolicy: PasswordPolicy = {
  minLength: 12,
  requireUppercase: true,
  requireNumber: true,
  requireSymbol: true,
  rotationDays: 90,
  historyDepth: 5,
};

// --- Help ---

export const mockArticles: KnowledgeArticle[] = [
  { id: "k1", title: "Launching your first multilingual campaign", category: "Getting started", excerpt: "Walk through building an audience, drafting content and scheduling delivery.", body: "", updatedAt: iso(10), readMinutes: 6 },
  { id: "k2", title: "Setting up SMS with DLT compliance", category: "Delivery", excerpt: "Configure MSG91 or Twilio with DLT-approved templates and sender IDs.", body: "", updatedAt: iso(20), readMinutes: 8 },
  { id: "k3", title: "Designing approval workflows", category: "Automation", excerpt: "Chain reviewers and approvers with escalation policies.", body: "", updatedAt: iso(5), readMinutes: 7 },
  { id: "k4", title: "Using AI content review responsibly", category: "AI Studio", excerpt: "Best practices for reviewing AI-generated regional content.", body: "", updatedAt: iso(3), readMinutes: 5 },
  { id: "k5", title: "Managing tenants and workspaces", category: "Administration", excerpt: "Understand tenant isolation, workspace roles and branding.", body: "", updatedAt: iso(15), readMinutes: 4 },
];

export const mockFaqs: Faq[] = [
  { id: "f1", question: "How is my workspace data isolated from other tenants?", answer: "Each workspace has a unique tenant ID; all queries and storage paths are scoped by tenant.", category: "Security" },
  { id: "f2", question: "Which languages are supported for AI translation?", answer: "English, Hindi, Tamil, Telugu, Marathi, Bengali, Kannada, Malayalam, Gujarati and Punjabi.", category: "AI Studio" },
  { id: "f3", question: "Can I export analytics reports?", answer: "Yes — CSV and JSON are available for every report; PDF and Excel are on the roadmap.", category: "Analytics" },
  { id: "f4", question: "How do I invite reviewers?", answer: "Open Settings → Users, invite by email and assign the Content Reviewer role.", category: "Users" },
];

export const mockShortcuts: KeyboardShortcut[] = [
  { keys: ["⌘", "K"], description: "Open command palette", category: "Navigation" },
  { keys: ["G", "D"], description: "Go to dashboard", category: "Navigation" },
  { keys: ["G", "C"], description: "Go to campaigns", category: "Navigation" },
  { keys: ["G", "A"], description: "Go to analytics", category: "Navigation" },
  { keys: ["N", "C"], description: "New campaign", category: "Create" },
  { keys: ["N", "T"], description: "New template", category: "Create" },
  { keys: ["?", ""], description: "Show keyboard shortcuts", category: "Help" },
  { keys: ["Esc"], description: "Close dialogs", category: "Navigation" },
];
