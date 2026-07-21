import type { CommunicationChannel } from "@/constants/india";

export type AiContentType =
  | "campaign_announcement"
  | "emergency_alert"
  | "healthcare_advisory"
  | "government_notice"
  | "university_announcement"
  | "ngo_awareness"
  | "corporate_communication"
  | "social_media_post"
  | "push_notification"
  | "sms"
  | "whatsapp"
  | "email"
  | "website_banner"
  | "press_release"
  | "speech"
  | "poster_text"
  | "custom";

export type AiGenerationMode =
  | "create"
  | "rewrite"
  | "expand"
  | "shorten"
  | "simplify"
  | "translate"
  | "improve_grammar"
  | "improve_tone";

export type AiTone =
  | "formal"
  | "friendly"
  | "professional"
  | "emergency"
  | "educational"
  | "motivational"
  | "neutral";

export type AiReadingLevel = "primary" | "secondary" | "college" | "professional";

export interface AiComplianceRule {
  id: string;
  label: string;
  description?: string;
}

export interface AiGenerationRequest {
  contentType: AiContentType;
  mode: AiGenerationMode;
  tone: AiTone;
  language: string;
  channel?: CommunicationChannel;
  objective?: string;
  audience?: string;
  organizationId?: string;
  campaignId?: string;
  readingLevel?: AiReadingLevel;
  wordLimit?: number;
  keywords?: string[];
  callToAction?: string;
  compliance?: string[];
  prompt: string;
  seedContent?: string;
  variables?: Record<string, string>;
}

export interface AiSuggestion {
  id: string;
  kind: "grammar" | "tone" | "compliance" | "translation" | "clarity" | "cta";
  severity: "info" | "warning" | "error";
  message: string;
  suggestion?: string;
  range?: { start: number; end: number };
}

export interface AiContentScores {
  readability: number;
  engagement: number;
  sentiment: number;
  contentScore: number;
  seoScore: number;
  accessibility: number;
}

export interface AiGenerationResult {
  id: string;
  requestId: string;
  contentType: AiContentType;
  mode: AiGenerationMode;
  tone: AiTone;
  language: string;
  content: string;
  characters: number;
  words: number;
  tokens: number;
  suggestions: AiSuggestion[];
  scores: AiContentScores;
  createdAt: string;
  model: string;
}

export type PromptCategory =
  | "government"
  | "healthcare"
  | "education"
  | "ngo"
  | "emergency"
  | "election"
  | "corporate"
  | "internal_communication"
  | "social_campaign"
  | "general";

export interface PromptTemplate {
  id: string;
  title: string;
  description: string;
  category: PromptCategory;
  body: string;
  tags: string[];
  variables: string[];
  favorite: boolean;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  usageCount: number;
}

export interface AiHistoryEntry {
  id: string;
  title: string;
  contentType: AiContentType;
  mode: AiGenerationMode;
  language: string;
  preview: string;
  content: string;
  scores: AiContentScores;
  createdBy: string;
  createdAt: string;
  campaignId?: string;
  versions: number;
}

export interface AiDraft {
  id: string;
  title: string;
  content: string;
  language: string;
  contentType: AiContentType;
  updatedAt: string;
  pinned: boolean;
  archived: boolean;
  autoSaved: boolean;
}
