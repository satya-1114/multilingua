// ============================================================================
// Translation platform types
//
// Two coexisting surfaces:
//   1. Legacy AI free-text translation (Translate / Batch) — kept for the
//      /translation workspace page.
//   2. Multilingual Content Platform (Phase 5) — per-entity translations,
//      jobs and locales. Consumed by /translations pages and services.
// ============================================================================

// ── Legacy free-text translation ────────────────────────────────────────────

export interface TranslationQualityScores {
  accuracy: number;
  readability: number;
  tone: number;
  consistency: number;
  grammar: number;
  accessibility: number;
}

export interface TranslationRequest {
  sourceLanguage: string;
  targetLanguage: string;
  content: string;

  // Required by backend AI translation endpoint
  workspaceId?: string;

  // Optional legacy options
  glossaryId?: string;
  preserveVariables?: boolean;
}

export interface TranslationResult {
  id: string;

  sourceLanguage: string;
  targetLanguage: string;

  sourceContent: string;
  translatedContent: string;

  scores: TranslationQualityScores;

  createdAt: string;
  createdBy: string;

  characters: number;
}

export interface BatchTranslationRequest {
  sourceLanguage: string;
  targetLanguages: string[];

  content: string;

  // Passed through to every translate() call
  workspaceId?: string;
}

export interface BatchTranslationResult {
  id: string;
  sourceLanguage: string;
  entries: TranslationResult[];
  createdAt: string;
}

export interface GlossaryTerm {
  id: string;
  source: string;
  translations: Record<string, string>;
  category?: string;
  notes?: string;
}

export interface Glossary {
  id: string;
  name: string;
  description?: string;
  termCount: number;
  updatedAt: string;
}
// ── Multilingual Content Platform ───────────────────────────────────────────

export const TRANSLATION_STATUSES = [
  "draft",
  "translated",
  "reviewed",
  "published",
] as const;
export type TranslationStatus = (typeof TRANSLATION_STATUSES)[number];

export const TRANSLATION_ENTITY_TYPES = [
  "disaster",
  "public_resource",
  "campaign",
  "organization",
] as const;
export type TranslationEntityType = (typeof TRANSLATION_ENTITY_TYPES)[number];

export const TRANSLATION_JOB_STATUSES = [
  "pending",
  "processing",
  "completed",
  "failed",
  "cancelled",
] as const;
export type TranslationJobStatus = (typeof TRANSLATION_JOB_STATUSES)[number];

export interface EntityTranslation {
  id: string;
  entityType: TranslationEntityType | string;
  entityId: string;
  locale: string;
  fieldName: string;
  translatedValue: string;
  status: TranslationStatus;
  sourceHash: string | null;
  translatedByUserId: string | null;
  reviewedByUserId: string | null;
  metadata: Record<string, unknown>;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface EntityTranslationInput {
  entityType: TranslationEntityType | string;
  entityId: string;
  locale: string;
  fieldName: string;
  translatedValue: string;
  status?: TranslationStatus;
  sourceHash?: string | null;
  metadata?: Record<string, unknown>;
}

export interface EntityTranslationUpdate {
  translatedValue?: string;
  status?: TranslationStatus;
  sourceHash?: string | null;
  metadata?: Record<string, unknown>;
}

export interface TranslationListQuery {
  page?: number;
  pageSize?: number;
  query?: string;
  entityType?: string;
  entityId?: string;
  locale?: string;
  status?: TranslationStatus;
  fieldName?: string;
  translatorId?: string;
  reviewerId?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
}

export interface TranslationJob {
  id: string;
  entityType: string;
  entityId: string;
  sourceLocale: string;
  targetLocale: string;
  status: TranslationJobStatus;
  provider: string | null;
  requestedByUserId: string | null;
  requestedAt: string | null;
  completedAt: string | null;
  metadata: Record<string, unknown>;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface TranslationJobInput {
  entityType: TranslationEntityType | string;
  entityId: string;
  sourceLocale: string;
  targetLocale: string;
  provider?: string;
  metadata?: Record<string, unknown>;
}

export interface TranslationJobListQuery {
  page?: number;
  pageSize?: number;
  entityType?: string;
  entityId?: string;
  status?: TranslationJobStatus;
  targetLocale?: string;
  requestedByUserId?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
}

export interface TranslationLocale {
  id: string;
  locale: string;
  displayName: string;
  nativeName: string | null;
  rtl: boolean;
  enabled: boolean;
  defaultLocale: boolean;
  sortOrder: number;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface TranslationLocaleInput {
  locale: string;
  displayName: string;
  nativeName?: string | null;
  rtl?: boolean;
  enabled?: boolean;
  defaultLocale?: boolean;
  sortOrder?: number;
}

export interface TranslationLocaleUpdate {
  displayName?: string;
  nativeName?: string | null;
  rtl?: boolean;
  enabled?: boolean;
  defaultLocale?: boolean;
  sortOrder?: number;
}
