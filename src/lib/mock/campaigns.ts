import type {
  Campaign,
  CampaignActivityEntry,
  CampaignApprovalEntry,
  CampaignCategory,
  CampaignPriority,
  CampaignStatus,
  CampaignType,
  CampaignVisibility,
} from "@/types/campaign";
import type { CommunicationTemplate, TemplateCategory, TemplateStatus } from "@/types/template";
import type { MediaAsset, MediaKind } from "@/types/media";
import { CAMPAIGN_COLORS } from "@/constants/campaign";
import { LANGUAGES } from "@/constants/india";
import { mockOrganizations, mockAudienceGroups } from "@/lib/mock/audience";

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(20260710);
const pick = <T>(arr: readonly T[]) => arr[Math.floor(rng() * arr.length)] as T;

function iso(daysAgo: number, jitterHours = 0): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - daysAgo);
  d.setUTCHours(d.getUTCHours() - jitterHours);
  return d.toISOString();
}

const CAMPAIGN_SEED: {
  name: string;
  description: string;
  type: CampaignType;
  category: CampaignCategory;
  priority: CampaignPriority;
  tags: string[];
  languages: string[];
}[] = [
  { name: "Monsoon Health Advisory 2026", description: "District-wide guidance on waterborne illness prevention during monsoon.", type: "healthcare", category: "healthcare", priority: "high", tags: ["monsoon", "advisory"], languages: ["en", "hi", "mr"] },
  { name: "Universal Immunization Drive — Phase III", description: "Booster and childhood immunization outreach across primary health centres.", type: "healthcare", category: "healthcare", priority: "critical", tags: ["immunization", "phc"], languages: ["en", "hi", "kn", "ta"] },
  { name: "Voter Registration Deadline Reminder", description: "Reminder to register before the upcoming state assembly rolls close.", type: "election", category: "election", priority: "high", tags: ["election", "voter-roll"], languages: ["en", "hi", "te"] },
  { name: "Cyclone Preparedness Broadcast — Odisha Coast", description: "Coastal community broadcast on evacuation zones and shelter locations.", type: "emergency", category: "emergency", priority: "critical", tags: ["cyclone", "evacuation"], languages: ["en", "or", "hi"] },
  { name: "PMKVY Skill Training Enrollment", description: "Youth outreach for the new skilling cohort under PMKVY.", type: "awareness", category: "government", priority: "medium", tags: ["skilling", "youth"], languages: ["en", "hi"] },
  { name: "IIT Placement Season Kickoff", description: "Announcement of placement schedule and recruiter list.", type: "notice", category: "education", priority: "medium", tags: ["placements"], languages: ["en"] },
  { name: "Malaria Awareness — Rural Bihar", description: "Village-level awareness broadcast during peak season.", type: "healthcare", category: "healthcare", priority: "high", tags: ["malaria", "rural"], languages: ["en", "hi"] },
  { name: "Digital India Literacy Workshop", description: "Community workshop registration for digital public infrastructure basics.", type: "education", category: "education", priority: "low", tags: ["digital-india"], languages: ["en", "hi"] },
  { name: "Employee Town Hall — Q3", description: "Internal quarterly update to all employees.", type: "internal", category: "corporate", priority: "low", tags: ["town-hall"], languages: ["en"] },
  { name: "Blood Donation Camp — Bengaluru", description: "City-wide donor mobilization on World Blood Donor Day.", type: "event", category: "healthcare", priority: "medium", tags: ["donation", "event"], languages: ["en", "kn"] },
  { name: "Kisan Credit Card Renewal Notice", description: "Reminder to farmers whose KCC accounts require annual renewal.", type: "notice", category: "government", priority: "medium", tags: ["farmers", "banking"], languages: ["en", "hi", "pa"] },
  { name: "Girl Child Education Scholarship", description: "Awareness on eligibility and application cycle for scholarships.", type: "awareness", category: "ngo", priority: "medium", tags: ["education", "scholarship"], languages: ["en", "hi", "ta", "kn"] },
  { name: "COVID Booster — Elderly Population", description: "Precautionary booster targeting citizens above 60.", type: "healthcare", category: "healthcare", priority: "high", tags: ["covid", "booster"], languages: ["en", "hi"] },
  { name: "Property Tax Filing Reminder", description: "Municipal reminder to property owners nearing the annual deadline.", type: "notice", category: "government", priority: "medium", tags: ["tax", "municipal"], languages: ["en", "mr"] },
  { name: "University Admission Merit List", description: "Publication of the first merit list for undergraduate programmes.", type: "notice", category: "education", priority: "high", tags: ["admissions"], languages: ["en", "hi"] },
  { name: "Rural Sanitation Field Visit", description: "Field-day mobilization for Swachh Bharat volunteers.", type: "awareness", category: "government", priority: "low", tags: ["sanitation", "swachh"], languages: ["en", "hi"] },
  { name: "Cybersecurity Advisory — Financial Fraud", description: "Advisory on OTP fraud and safe UPI practices.", type: "advisory", category: "government", priority: "high", tags: ["cyber", "fraud"], languages: ["en", "hi", "ta"] },
  { name: "Flood Relief Volunteer Mobilization", description: "Emergency volunteer call for flood-affected districts.", type: "emergency", category: "ngo", priority: "critical", tags: ["floods", "volunteers"], languages: ["en", "hi", "as"] },
];

const STATUSES: CampaignStatus[] = [
  "draft", "pending_approval", "approved", "scheduled", "running",
  "completed", "cancelled", "archived", "failed",
];

const OWNERS = [
  { id: "user-1", name: "Ananya Iyer", role: "Campaign Manager" },
  { id: "user-2", name: "Rahul Verma", role: "Communication Officer" },
  { id: "user-3", name: "Priya Nair", role: "Org Admin" },
  { id: "user-4", name: "Vikram Reddy", role: "Content Creator" },
  { id: "user-5", name: "Meera Krishnan", role: "Campaign Manager" },
  { id: "user-6", name: "Arjun Sharma", role: "Communication Officer" },
];

function makeApprovals(status: CampaignStatus, createdAt: string): CampaignApprovalEntry[] {
  if (status === "draft") return [];
  const approver = pick(OWNERS);
  const submittedAt = new Date(createdAt);
  submittedAt.setDate(submittedAt.getDate() + 1);
  const base: CampaignApprovalEntry[] = [
    {
      id: `apr-${crypto.randomUUID?.().slice(0, 6) ?? Math.random().toString(36).slice(2, 8)}`,
      actorId: approver.id,
      actorName: approver.name,
      actorRole: approver.role,
      status: "pending",
      comment: "Submitted for regulatory review.",
      at: submittedAt.toISOString(),
    },
  ];
  if (status === "pending_approval") return base;
  const decisionAt = new Date(submittedAt);
  decisionAt.setHours(decisionAt.getHours() + 6);
  const decision: CampaignApprovalEntry["status"] =
    status === "cancelled" || status === "failed" ? "rejected" : "approved";
  base.push({
    id: `apr-${crypto.randomUUID?.().slice(0, 6) ?? Math.random().toString(36).slice(2, 8)}`,
    actorId: approver.id,
    actorName: approver.name,
    actorRole: approver.role,
    status: decision,
    comment: decision === "approved" ? "Content and audience verified." : "Language variants need review.",
    at: decisionAt.toISOString(),
  });
  return base;
}

function makeActivity(status: CampaignStatus, createdAt: string, updatedAt: string): CampaignActivityEntry[] {
  const events: CampaignActivityEntry[] = [
    { id: "a1", type: "created", message: "Campaign draft created", actor: "System", at: createdAt },
  ];
  if (status !== "draft") {
    events.push({ id: "a2", type: "submitted", message: "Submitted for approval", actor: pick(OWNERS).name, at: new Date(new Date(createdAt).getTime() + 3600_000).toISOString() });
  }
  if (["approved", "scheduled", "running", "completed", "archived"].includes(status)) {
    events.push({ id: "a3", type: "approved", message: "Approved by reviewer", actor: pick(OWNERS).name, at: new Date(new Date(createdAt).getTime() + 7200_000).toISOString() });
  }
  if (["running", "completed", "archived"].includes(status)) {
    events.push({ id: "a4", type: "launched", message: "Campaign launched to audience", actor: pick(OWNERS).name, at: new Date(new Date(createdAt).getTime() + 86400_000).toISOString() });
  }
  if (["completed", "archived"].includes(status)) {
    events.push({ id: "a5", type: "status_changed", message: "Marked as completed", actor: "System", at: updatedAt });
  }
  if (status === "cancelled") {
    events.push({ id: "a6", type: "cancelled", message: "Campaign cancelled", actor: pick(OWNERS).name, at: updatedAt });
  }
  return events;
}

function makeCampaign(idx: number): Campaign {
  const seed = CAMPAIGN_SEED[idx % CAMPAIGN_SEED.length]!;
  const status: CampaignStatus =
    idx < 4 ? "draft" :
    idx < 8 ? "pending_approval" :
    idx < 12 ? "approved" :
    idx < 20 ? "scheduled" :
    idx < 28 ? "running" :
    idx < 40 ? "completed" :
    idx < 46 ? "archived" :
    idx < 50 ? "cancelled" : "failed";

  const org = pick(mockOrganizations);
  const owner = pick(OWNERS);
  const createdDaysAgo = 3 + Math.floor(rng() * 90);
  const createdAt = iso(createdDaysAgo, Math.floor(rng() * 20));
  const updatedAt = iso(Math.max(1, Math.floor(rng() * createdDaysAgo)));
  const startAt = iso(-(3 + Math.floor(rng() * 40)) + (["completed", "archived"].includes(status) ? 30 : 0));
  const endAt = iso(-(6 + Math.floor(rng() * 20)));
  const visibility: CampaignVisibility = pick(["organization", "public", "private"] as const);
  const groupIds = mockAudienceGroups
    .slice(0, 1 + Math.floor(rng() * 3))
    .map((g) => g.id);

  return {
    id: `cmp-${(idx + 1).toString().padStart(4, "0")}`,
    code: `CMP-${new Date(createdAt).getFullYear()}-${(idx + 1).toString().padStart(4, "0")}`,
    name: seed.name,
    description: seed.description,
    objective: `Reach ${(50 + Math.floor(rng() * 400)) * 100} beneficiaries with clear, localized messaging.`,
    type: seed.type,
    category: seed.category,
    priority: seed.priority,
    visibility,
    status,
    color: pick(CAMPAIGN_COLORS),
    tags: seed.tags,
    organizationId: org.id,
    organizationName: org.name,
    department: pick(["Outreach", "Field", "Communications", "Public Health", "Administration"]),
    ownerId: owner.id,
    ownerName: owner.name,
    audienceGroupIds: groupIds,
    audienceContactIds: [],
    estimatedReach: groupIds.reduce(
      (sum, id) => sum + (mockAudienceGroups.find((g) => g.id === id)?.memberCount ?? 0),
      0,
    ),
    languages: seed.languages,
    templateId: `tpl-${1 + (idx % 8)}`,
    templateName: seed.name.split(" ").slice(0, 3).join(" ") + " Template",
    schedule: {
      mode: status === "draft" ? "draft" : status === "scheduled" ? "schedule" : "publish_now",
      timezone: "Asia/Kolkata",
      startAt,
      endAt,
    },
    approvals: makeApprovals(status, createdAt),
    activity: makeActivity(status, createdAt, updatedAt),
    notes: rng() > 0.6
      ? [
          {
            id: "n1",
            body: "Confirm SMS gateway throughput before launch window.",
            authorId: owner.id,
            authorName: owner.name,
            pinned: rng() > 0.7,
            createdAt,
          },
        ]
      : [],
    createdAt,
    updatedAt,
    launchedAt: ["running", "completed", "archived"].includes(status) ? startAt : undefined,
    completedAt: ["completed", "archived"].includes(status) ? endAt : undefined,
    archivedAt: status === "archived" ? updatedAt : undefined,
  };
}

export const mockCampaigns: Campaign[] = Array.from({ length: 54 }, (_, i) => makeCampaign(i));

// ─── Templates ───────────────────────────────────────────────────────────

const TEMPLATE_SEED: {
  name: string;
  category: TemplateCategory;
  language: string;
  status: TemplateStatus;
  subject?: string;
  body: string;
}[] = [
  {
    name: "Vaccination Reminder — SMS",
    category: "sms",
    language: "en",
    status: "published",
    body: "Hello {{first_name}}, your child's vaccination is due on {{date}} at {{city}} PHC. Please carry the immunization card. — {{organization}}",
  },
  {
    name: "Cyclone Evacuation Alert — Hindi",
    category: "emergency_alert",
    language: "hi",
    status: "published",
    body: "आपात सूचना: {{district}} में चक्रवात की चेतावनी। {{date}} तक निकटतम आश्रय स्थल पहुँचें। — {{organization}}",
  },
  {
    name: "Voter Registration Reminder",
    category: "email",
    language: "en",
    status: "published",
    subject: "You have 5 days to register — {{state}}",
    body: "Dear {{first_name}} {{last_name}},\n\nElectoral rolls for {{state}} close on {{date}}. Register at your booth in {{district}} to ensure your vote counts.\n\nRegards,\n{{organization}}",
  },
  {
    name: "Monsoon Health Advisory — Marathi",
    category: "government_notice",
    language: "mr",
    status: "published",
    subject: "पावसाळी आरोग्य सूचना",
    body: "नमस्कार {{first_name}}, पावसाळ्यात उकळलेले पाणी प्या आणि साचलेल्या पाण्याजवळ जाणे टाळा. जवळचा दवाखाना: {{city}} पीएचसी.",
  },
  {
    name: "Placement Schedule — Email",
    category: "email",
    language: "en",
    status: "published",
    subject: "Placement Season 2026 — Registration Open",
    body: "Hello {{first_name}},\n\nRegistration for Placement Season 2026 is now open. Please complete your profile by {{date}}.\n\n— {{organization}}",
  },
  {
    name: "Community Blood Donation Camp — WhatsApp",
    category: "whatsapp",
    language: "kn",
    status: "published",
    body: "ನಮಸ್ಕಾರ {{first_name}}, {{date}} ರಂದು {{city}} ದಲ್ಲಿ ರಕ್ತದಾನ ಶಿಬಿರ ನಡೆಯಲಿದೆ. ದಯವಿಟ್ಟು ಭಾಗವಹಿಸಿ.",
  },
  {
    name: "Property Tax Reminder — SMS",
    category: "sms",
    language: "en",
    status: "published",
    body: "Reminder: {{first_name}}, please file your {{city}} municipal property tax before {{date}} to avoid late fees.",
  },
  {
    name: "Employee Town Hall Invite",
    category: "email",
    language: "en",
    status: "draft",
    subject: "Q3 Town Hall — {{date}} at {{time}}",
    body: "Hi {{first_name}},\n\nJoin the Q3 town hall on {{date}} at {{time}}. Agenda and dial-in details will follow.\n\n— Communications, {{organization}}",
  },
  {
    name: "Scholarship Application — Tamil",
    category: "sms",
    language: "ta",
    status: "published",
    body: "வணக்கம் {{first_name}}, மாணவிகளுக்கான உதவித்தொகைக்கு {{date}} க்கு முன் விண்ணப்பியுங்கள். — {{organization}}",
  },
  {
    name: "Cybersecurity Advisory — Push",
    category: "push",
    language: "en",
    status: "published",
    body: "Never share OTPs. Verify UPI requests carefully. — {{organization}}",
  },
  {
    name: "Digital Literacy Workshop — Website Banner",
    category: "banner",
    language: "en",
    status: "published",
    body: "Register today: Free Digital India literacy workshop in {{city}} on {{date}}.",
  },
  {
    name: "Kisan Credit Renewal — Punjabi",
    category: "sms",
    language: "pa",
    status: "published",
    body: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ {{first_name}}, ਤੁਹਾਡਾ ਕਿਸਾਨ ਕ੍ਰੈਡਿਟ ਕਾਰਡ {{date}} ਤੱਕ ਨਵਿਆਉਣਾ ਹੈ।",
  },
  {
    name: "Immunization Follow-up — Telugu",
    category: "whatsapp",
    language: "te",
    status: "published",
    body: "నమస్కారం {{first_name}}, {{date}} నాటికి మీ పిల్లల టీకా బాకీ ఉంది. దయచేసి {{city}} PHC సందర్శించండి.",
  },
];

export const mockTemplates: CommunicationTemplate[] = TEMPLATE_SEED.map((t, i) => {
  const createdAt = iso(30 + i * 4);
  const updatedAt = iso(Math.floor(rng() * 20));
  const authorId = pick(OWNERS).id;
  const authorName = OWNERS.find((o) => o.id === authorId)?.name ?? "Ananya Iyer";
  const version = 1 + Math.floor(rng() * 3);
  return {
    id: `tpl-${i + 1}`,
    name: t.name,
    category: t.category,
    language: t.language,
    status: t.status,
    subject: t.subject,
    body: t.body,
    variables: [],
    version,
    versions: Array.from({ length: version }, (_, v) => ({
      id: `tpl-${i + 1}-v${v + 1}`,
      version: v + 1,
      subject: t.subject,
      body: t.body,
      authorId,
      authorName,
      note: v === 0 ? "Initial version" : "Language and tone refinements",
      createdAt: iso(30 + i * 4 - v * 3),
    })),
    usageCount: Math.floor(rng() * 40),
    createdBy: authorId,
    createdByName: authorName,
    createdAt,
    updatedAt,
  };
});

// ─── Media library ───────────────────────────────────────────────────────

const MEDIA_SEED: { name: string; kind: MediaKind; mime: string; size: number }[] = [
  { name: "Immunization Poster.pdf", kind: "document", mime: "application/pdf", size: 812_431 },
  { name: "Monsoon Advisory Banner.png", kind: "image", mime: "image/png", size: 240_120 },
  { name: "Cyclone Preparedness Flyer.pdf", kind: "document", mime: "application/pdf", size: 640_224 },
  { name: "Voter Roll Infographic.jpg", kind: "image", mime: "image/jpeg", size: 320_000 },
  { name: "Scholarship Application Form.docx", kind: "document", mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", size: 128_432 },
  { name: "Digital Literacy Poster.png", kind: "image", mime: "image/png", size: 180_240 },
  { name: "Town Hall Agenda.pdf", kind: "document", mime: "application/pdf", size: 96_120 },
  { name: "Blood Donation Camp.jpg", kind: "image", mime: "image/jpeg", size: 512_000 },
  { name: "Municipal Circular 2026-04.pdf", kind: "document", mime: "application/pdf", size: 220_100 },
  { name: "Rural Sanitation Brochure.pdf", kind: "document", mime: "application/pdf", size: 305_240 },
];

export const mockMedia: MediaAsset[] = MEDIA_SEED.map((m, i) => ({
  id: `med-${i + 1}`,
  name: m.name,
  kind: m.kind,
  mimeType: m.mime,
  sizeBytes: m.size,
  url: "#",
  uploadedById: pick(OWNERS).id,
  uploadedByName: pick(OWNERS).name,
  favorite: i % 4 === 0,
  tags: [pick(["campaign", "advisory", "banner", "notice"])],
  createdAt: iso(5 + i * 3),
}));

export { STATUSES as MOCK_CAMPAIGN_STATUSES };
