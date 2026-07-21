import type {
  CampaignCategory,
  CampaignPriority,
  CampaignStatus,
  CampaignType,
  CampaignVisibility,
} from "@/types/campaign";

export const CAMPAIGN_STATUSES: {
  key: CampaignStatus;
  label: string;
  tone: "muted" | "primary" | "accent" | "warning" | "success" | "danger";
  description: string;
}[] = [
  { key: "draft", label: "Draft", tone: "muted", description: "Being edited, not yet submitted." },
  { key: "pending_approval", label: "Pending approval", tone: "warning", description: "Awaiting reviewer action." },
  { key: "approved", label: "Approved", tone: "accent", description: "Cleared for scheduling." },
  { key: "scheduled", label: "Scheduled", tone: "primary", description: "Queued for a future start time." },
  { key: "running", label: "Running", tone: "primary", description: "Currently sending." },
  { key: "completed", label: "Completed", tone: "success", description: "All deliveries finished." },
  { key: "cancelled", label: "Cancelled", tone: "danger", description: "Halted before completion." },
  { key: "archived", label: "Archived", tone: "muted", description: "Moved out of active workspace." },
  { key: "failed", label: "Failed", tone: "danger", description: "Blocked by a delivery error." },
];

export const CAMPAIGN_STATUS_META: Record<CampaignStatus, (typeof CAMPAIGN_STATUSES)[number]> =
  Object.fromEntries(CAMPAIGN_STATUSES.map((s) => [s.key, s])) as Record<
    CampaignStatus,
    (typeof CAMPAIGN_STATUSES)[number]
  >;

export const CAMPAIGN_TRANSITIONS: Record<CampaignStatus, CampaignStatus[]> = {
  draft: ["pending_approval", "archived"],
  pending_approval: ["approved", "draft", "cancelled"],
  approved: ["scheduled", "running", "cancelled", "draft"],
  scheduled: ["running", "cancelled", "draft"],
  running: ["completed", "cancelled", "failed"],
  completed: ["archived"],
  cancelled: ["archived", "draft"],
  archived: ["draft"],
  failed: ["draft", "archived"],
};

export const WORKFLOW_STEPS: { key: CampaignStatus; label: string }[] = [
  { key: "draft", label: "Draft" },
  { key: "pending_approval", label: "Approval" },
  { key: "approved", label: "Approved" },
  { key: "scheduled", label: "Scheduled" },
  { key: "running", label: "Running" },
  { key: "completed", label: "Completed" },
];

export const CAMPAIGN_TYPES: { key: CampaignType; label: string; description: string }[] = [
  { key: "awareness", label: "Public Awareness", description: "General awareness and outreach." },
  { key: "advisory", label: "Advisory", description: "Guidance or recommendation." },
  { key: "emergency", label: "Emergency Alert", description: "Time-critical safety broadcast." },
  { key: "notice", label: "Official Notice", description: "Formal notice or announcement." },
  { key: "survey", label: "Survey", description: "Data-collection outreach." },
  { key: "event", label: "Event", description: "Event invitation or reminder." },
  { key: "internal", label: "Internal", description: "Internal staff communication." },
  { key: "election", label: "Election Notice", description: "Electoral announcement." },
  { key: "healthcare", label: "Healthcare", description: "Health programme communication." },
  { key: "education", label: "Education", description: "Academic or training update." },
];

export const CAMPAIGN_PRIORITIES: { key: CampaignPriority; label: string }[] = [
  { key: "low", label: "Low" },
  { key: "medium", label: "Medium" },
  { key: "high", label: "High" },
  { key: "critical", label: "Critical" },
];

export const CAMPAIGN_CATEGORIES: { key: CampaignCategory; label: string }[] = [
  { key: "government", label: "Government" },
  { key: "healthcare", label: "Healthcare" },
  { key: "education", label: "Education" },
  { key: "ngo", label: "NGO" },
  { key: "corporate", label: "Corporate" },
  { key: "emergency", label: "Emergency" },
  { key: "election", label: "Election" },
  { key: "custom", label: "Custom" },
];

export const CAMPAIGN_VISIBILITIES: { key: CampaignVisibility; label: string; description: string }[] = [
  { key: "private", label: "Private", description: "Only the owner can see this campaign." },
  { key: "organization", label: "Organization", description: "Visible to your organization." },
  { key: "public", label: "Public", description: "Visible across the workspace." },
];

export const CAMPAIGN_COLORS = [
  "#2563EB",
  "#7C3AED",
  "#DB2777",
  "#DC2626",
  "#EA580C",
  "#CA8A04",
  "#16A34A",
  "#0891B2",
  "#0F766E",
  "#475569",
];

export function isTransitionAllowed(from: CampaignStatus, to: CampaignStatus): boolean {
  return CAMPAIGN_TRANSITIONS[from]?.includes(to) ?? false;
}
