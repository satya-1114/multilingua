import type {
  AiContentScores,
  AiContentType,
  AiDraft,
  AiGenerationMode,
  AiHistoryEntry,
  AiSuggestion,
  AiTone,
  PromptTemplate,
} from "@/types/ai";
import type { JobRecord } from "@/types/jobs";

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
const rng = mulberry32(20260706);
const pick = <T>(arr: readonly T[]) => arr[Math.floor(rng() * arr.length)] as T;
const daysAgo = (n: number) => new Date(Date.now() - n * 86_400_000).toISOString();

export function synthScores(seed = 0): AiContentScores {
  const r = mulberry32(seed || Math.floor(rng() * 10_000));
  const clamp = (v: number) => Math.max(55, Math.min(98, Math.round(v)));
  return {
    readability: clamp(70 + r() * 25),
    engagement: clamp(65 + r() * 30),
    sentiment: clamp(60 + r() * 35),
    contentScore: clamp(70 + r() * 25),
    seoScore: clamp(55 + r() * 40),
    accessibility: clamp(70 + r() * 25),
  };
}

export function synthSuggestions(): AiSuggestion[] {
  return [
    {
      id: "s1",
      kind: "grammar",
      severity: "info",
      message: "Consider active voice in the second sentence.",
    },
    {
      id: "s2",
      kind: "tone",
      severity: "warning",
      message: "The closing feels overly formal for a WhatsApp audience.",
      suggestion: "Try a warmer sign-off such as \"Stay safe.\"",
    },
    {
      id: "s3",
      kind: "compliance",
      severity: "info",
      message: "Include the official issuing department for citizen notices.",
    },
    {
      id: "s4",
      kind: "clarity",
      severity: "info",
      message: "Shorten the third sentence for SMS delivery under 160 characters.",
    },
  ];
}

export const mockPrompts: PromptTemplate[] = [
  {
    id: "prompt-flood-alert",
    title: "District flood alert",
    description: "Emergency alert template for imminent flooding in Indian districts.",
    category: "emergency",
    body: "Draft an urgent flood alert for residents of {{district}} in {{language}}. Include evacuation routes, helpline {{helpline}}, and issuing department {{department}}.",
    tags: ["flood", "disaster", "sms"],
    variables: ["district", "language", "helpline", "department"],
    favorite: true,
    createdBy: "Ananya Rao",
    createdAt: daysAgo(28),
    updatedAt: daysAgo(3),
    usageCount: 42,
  },
  {
    id: "prompt-vaccination",
    title: "Childhood vaccination reminder",
    description: "Friendly SMS reminder for the next vaccination visit.",
    category: "healthcare",
    body: "Write a friendly reminder to {{recipient_name}} about the {{event}} vaccination visit at {{time}} on {{date}}. Sign off from {{organization}}.",
    tags: ["vaccination", "sms", "reminder"],
    variables: ["recipient_name", "event", "time", "date", "organization"],
    favorite: true,
    createdBy: "Dr. Vinay Menon",
    createdAt: daysAgo(60),
    updatedAt: daysAgo(9),
    usageCount: 128,
  },
  {
    id: "prompt-scholarship",
    title: "Scholarship application notice",
    description: "Government notice announcing scholarship applications.",
    category: "government",
    body: "Announce the {{event}} scholarship application window on behalf of {{department}}. Include eligibility, deadline {{date}} and portal link.",
    tags: ["scholarship", "education", "notice"],
    variables: ["event", "department", "date"],
    favorite: false,
    createdBy: "Priya Sharma",
    createdAt: daysAgo(90),
    updatedAt: daysAgo(30),
    usageCount: 76,
  },
  {
    id: "prompt-election-awareness",
    title: "Voter awareness message",
    description: "Neutral, non-partisan reminder to vote on polling day.",
    category: "election",
    body: "Write a non-partisan reminder for voters in {{district}} for polling on {{date}}. Encourage carrying voter ID.",
    tags: ["election", "voter"],
    variables: ["district", "date"],
    favorite: false,
    createdBy: "Rahul Iyer",
    createdAt: daysAgo(120),
    updatedAt: daysAgo(45),
    usageCount: 210,
  },
  {
    id: "prompt-university-circular",
    title: "University semester circular",
    description: "Official circular for semester schedule updates.",
    category: "education",
    body: "Draft a circular from {{organization}} for {{event}} affecting all students. Include revised schedule, contact {{department}}.",
    tags: ["university", "circular"],
    variables: ["organization", "event", "department"],
    favorite: false,
    createdBy: "Registrar Office",
    createdAt: daysAgo(55),
    updatedAt: daysAgo(12),
    usageCount: 34,
  },
  {
    id: "prompt-ngo-awareness",
    title: "Menstrual health awareness",
    description: "Community-friendly message for menstrual health awareness sessions.",
    category: "ngo",
    body: "Invite women in {{city}} to a menstrual health awareness session on {{date}} at {{time}}. Organised by {{organization}}.",
    tags: ["ngo", "awareness", "health"],
    variables: ["city", "date", "time", "organization"],
    favorite: true,
    createdBy: "Sneha Kulkarni",
    createdAt: daysAgo(20),
    updatedAt: daysAgo(2),
    usageCount: 18,
  },
  {
    id: "prompt-corporate-townhall",
    title: "Corporate town-hall invitation",
    description: "Formal invite for a company-wide town-hall.",
    category: "corporate",
    body: "Invite all employees of {{organization}} to a town-hall on {{date}} at {{time}}, hosted by {{department}}.",
    tags: ["townhall", "internal"],
    variables: ["organization", "date", "time", "department"],
    favorite: false,
    createdBy: "People Ops",
    createdAt: daysAgo(15),
    updatedAt: daysAgo(1),
    usageCount: 9,
  },
];

const historyTitles = [
  "Monsoon health advisory — Bengaluru",
  "PMAY beneficiary confirmation SMS",
  "Cyclone Yaas emergency broadcast — Odisha coast",
  "Voter registration drive — Chennai north",
  "Scholarship deadline reminder — batch 2026",
  "Water conservation drive — Pune",
  "Digital literacy workshop invite — Warangal",
  "Polio immunisation Sunday reminder",
  "Anti-ragging awareness — Delhi University",
  "Farmer subsidy portal notice — Punjab",
];

const historyContentTypes: AiContentType[] = [
  "healthcare_advisory",
  "sms",
  "emergency_alert",
  "government_notice",
  "email",
  "social_media_post",
  "campaign_announcement",
  "whatsapp",
];

const historyLanguages = ["en", "hi", "ta", "te", "kn", "mr", "bn", "ml"];
const historyModes: AiGenerationMode[] = [
  "create",
  "rewrite",
  "translate",
  "simplify",
  "improve_tone",
];
const historyPeople = [
  "Ananya Rao",
  "Rahul Iyer",
  "Priya Sharma",
  "Dr. Vinay Menon",
  "Sneha Kulkarni",
];

export const mockAiHistory: AiHistoryEntry[] = historyTitles.map((title, i) => ({
  id: `ai-hist-${i + 1}`,
  title,
  contentType: historyContentTypes[i % historyContentTypes.length]!,
  mode: historyModes[i % historyModes.length]!,
  language: historyLanguages[i % historyLanguages.length]!,
  preview:
    "Draft prepared and reviewed by the communications team. Includes translation and channel-optimised phrasing.",
  content:
    "Full generated content preserved for audit. Multilingual variants attached automatically for review.",
  scores: synthScores(i + 11),
  createdBy: historyPeople[i % historyPeople.length]!,
  createdAt: daysAgo(i * 2 + 1),
  campaignId: `cmp-${(i % 6) + 1}`,
  versions: 1 + (i % 4),
}));

export const mockAiDrafts: AiDraft[] = [
  {
    id: "draft-1",
    title: "Untitled — Cyclone shelter advisory",
    content: "Residents of coastal Odisha are advised to move to designated cyclone shelters…",
    language: "en",
    contentType: "emergency_alert",
    updatedAt: daysAgo(0.02),
    pinned: true,
    archived: false,
    autoSaved: true,
  },
  {
    id: "draft-2",
    title: "Scholarship reminder — v3",
    content: "Applications for the Chief Minister's Merit Scholarship close on 30 Nov 2026…",
    language: "hi",
    contentType: "government_notice",
    updatedAt: daysAgo(0.5),
    pinned: false,
    archived: false,
    autoSaved: true,
  },
  {
    id: "draft-3",
    title: "Health check camp invite",
    content: "Free general health check camp on Sunday at the community centre…",
    language: "ta",
    contentType: "healthcare_advisory",
    updatedAt: daysAgo(2),
    pinned: false,
    archived: false,
    autoSaved: false,
  },
  {
    id: "draft-4",
    title: "Archived — 2025 town hall invite",
    content: "Town hall invitation retained for reference…",
    language: "en",
    contentType: "corporate_communication",
    updatedAt: daysAgo(120),
    pinned: false,
    archived: true,
    autoSaved: false,
  },
];

export const mockJobs: JobRecord[] = [
  {
    id: "job-1",
    kind: "ai_generation",
    title: "AI generation · Monsoon advisory batch",
    status: "running",
    progress: 62,
    total: 8,
    processed: 5,
    createdBy: "Ananya Rao",
    createdAt: daysAgo(0.01),
    updatedAt: daysAgo(0.005),
    startedAt: daysAgo(0.008),
  },
  {
    id: "job-2",
    kind: "translation",
    title: "Batch translate — 12 languages",
    status: "queued",
    progress: 0,
    total: 12,
    processed: 0,
    createdBy: "Priya Sharma",
    createdAt: daysAgo(0.02),
    updatedAt: daysAgo(0.02),
  },
  {
    id: "job-3",
    kind: "bulk_delivery",
    title: "SMS delivery — 24k recipients",
    status: "completed",
    progress: 100,
    total: 24_000,
    processed: 24_000,
    createdBy: "Communication Officer",
    createdAt: daysAgo(1),
    updatedAt: daysAgo(0.9),
    startedAt: daysAgo(0.98),
    completedAt: daysAgo(0.9),
  },
  {
    id: "job-4",
    kind: "audience_import",
    title: "Audience import — Karnataka farmers CSV",
    status: "failed",
    progress: 34,
    total: 12_000,
    processed: 4_080,
    createdBy: "Rahul Iyer",
    createdAt: daysAgo(2),
    updatedAt: daysAgo(2),
    startedAt: daysAgo(2),
    errorMessage: "Row 4,081 · duplicate phone number detected. Fix source file and retry.",
  },
  {
    id: "job-5",
    kind: "export",
    title: "Export delivery report — Oct 2026",
    status: "completed",
    progress: 100,
    createdBy: "Data Analyst",
    createdAt: daysAgo(4),
    updatedAt: daysAgo(4),
    startedAt: daysAgo(4),
    completedAt: daysAgo(3.99),
  },
];

export function fakeGeneratedContent(
  prompt: string,
  tone: AiTone,
  language: string,
): string {
  const salutation =
    language === "hi"
      ? "प्रिय नागरिक,"
      : language === "ta"
        ? "அன்பு குடிமகனே,"
        : language === "te"
          ? "గౌరవనీయ పౌరా,"
          : "Dear citizen,";
  const closing =
    tone === "emergency"
      ? "Please act on this alert without delay."
      : tone === "friendly"
        ? "Thank you for supporting our community."
        : "Regards, District Communications Office.";
  const body = `${salutation}\n\n${prompt.trim()}\n\nThis message has been generated with tone: ${tone}. Please review before dispatch.\n\n${closing}`;
  return body;
}

export { pick };
