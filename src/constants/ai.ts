import type {
  AiContentType,
  AiGenerationMode,
  AiReadingLevel,
  AiTone,
  PromptCategory,
} from "@/types/ai";

export const AI_CONTENT_TYPES: { key: AiContentType; label: string; group: string }[] = [
  { key: "campaign_announcement", label: "Campaign announcement", group: "Campaigns" },
  { key: "emergency_alert", label: "Emergency alert", group: "Public safety" },
  { key: "healthcare_advisory", label: "Healthcare advisory", group: "Public safety" },
  { key: "government_notice", label: "Government notice", group: "Government" },
  { key: "university_announcement", label: "University announcement", group: "Education" },
  { key: "ngo_awareness", label: "NGO awareness", group: "NGO" },
  { key: "corporate_communication", label: "Corporate communication", group: "Corporate" },
  { key: "social_media_post", label: "Social media post", group: "Channels" },
  { key: "push_notification", label: "Push notification", group: "Channels" },
  { key: "sms", label: "SMS", group: "Channels" },
  { key: "whatsapp", label: "WhatsApp message", group: "Channels" },
  { key: "email", label: "Email", group: "Channels" },
  { key: "website_banner", label: "Website banner", group: "Web" },
  { key: "press_release", label: "Press release", group: "Media" },
  { key: "speech", label: "Speech", group: "Media" },
  { key: "poster_text", label: "Poster text", group: "Print" },
  { key: "custom", label: "Custom prompt", group: "Other" },
];

export const AI_GENERATION_MODES: { key: AiGenerationMode; label: string }[] = [
  { key: "create", label: "Create" },
  { key: "rewrite", label: "Rewrite" },
  { key: "expand", label: "Expand" },
  { key: "shorten", label: "Shorten" },
  { key: "simplify", label: "Simplify" },
  { key: "translate", label: "Translate" },
  { key: "improve_grammar", label: "Improve grammar" },
  { key: "improve_tone", label: "Improve tone" },
];

export const AI_TONES: { key: AiTone; label: string }[] = [
  { key: "formal", label: "Formal" },
  { key: "friendly", label: "Friendly" },
  { key: "professional", label: "Professional" },
  { key: "emergency", label: "Emergency" },
  { key: "educational", label: "Educational" },
  { key: "motivational", label: "Motivational" },
  { key: "neutral", label: "Neutral" },
];

export const AI_READING_LEVELS: { key: AiReadingLevel; label: string }[] = [
  { key: "primary", label: "Primary school" },
  { key: "secondary", label: "Secondary school" },
  { key: "college", label: "College" },
  { key: "professional", label: "Professional" },
];

export const PROMPT_CATEGORIES: { key: PromptCategory; label: string }[] = [
  { key: "government", label: "Government" },
  { key: "healthcare", label: "Healthcare" },
  { key: "education", label: "Education" },
  { key: "ngo", label: "NGO" },
  { key: "emergency", label: "Emergency" },
  { key: "election", label: "Election" },
  { key: "corporate", label: "Corporate" },
  { key: "internal_communication", label: "Internal communication" },
  { key: "social_campaign", label: "Social campaign" },
  { key: "general", label: "General" },
];

export const AI_STANDARD_VARIABLES = [
  "organization",
  "campaign",
  "language",
  "district",
  "city",
  "recipient_name",
  "department",
  "date",
  "time",
  "event",
];

export const AI_COMPLIANCE_RULES = [
  { id: "no_pii", label: "No PII in outbound messages" },
  { id: "official_language", label: "Use official language guidelines" },
  { id: "election_code", label: "Follow Election Commission code" },
  { id: "healthcare_disclaimer", label: "Include healthcare disclaimer" },
  { id: "brand_voice", label: "Match organization brand voice" },
];
