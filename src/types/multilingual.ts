/**
 * Multilingual content types.
 *
 * A single Campaign or Disaster owns ONE multilingual record. Each supported
 * language is stored as an entry inside that record — never as a duplicate
 * parent entity. All entries share the parent's identity, status, and audit
 * trail.
 *
 * Backend contract documented in `docs/BACKEND-MULTILINGUAL.md`.
 */

export type TranslationStatus = "draft" | "generated" | "edited" | "published";

export type MultilingualParentType = "campaign" | "disaster";

export type AiVariantKind =
  | "summary"
  | "short_announcement"
  | "emergency_sms"
  | "social_post"
  | "poster_text"
  | "speech_script"
  | "radio_announcement"
  | "voice_announcement";

export interface AudioAsset {
  /** Media asset id in the existing media store (see `mediaService`). */
  mediaId: string;
  url: string;
  mimeType: string;
  durationSeconds?: number;
  sizeBytes?: number;
  voice?: string;
  generatedAt: string;
  /** True when the audio was produced from an edited (human-approved) translation. */
  fromEditedTranslation?: boolean;
}

export interface TranslationEntry {
  language: string;
  /** Translated body text. May be empty until `status !== "draft"`. */
  content: string;
  /** Optional translated title/heading. */
  title?: string;
  /** Optional translated safety instructions (disasters only). */
  safetyInstructions?: string;
  status: TranslationStatus;
  audio?: AudioAsset;
  /** AI-generated variants (summary, sms, poster, …) scoped to this language. */
  variants?: Partial<Record<AiVariantKind, string>>;
  updatedAt: string;
  updatedBy?: string;
}

export interface MultilingualContent {
  parentType: MultilingualParentType;
  parentId: string;
  /** Language code of the authored source (e.g. "en"). */
  sourceLanguage: string;
  /** All supported target languages including the source. */
  entries: TranslationEntry[];
  updatedAt: string;
}

export interface GenerateTranslationRequest {
  targetLanguages: string[];
  /** Force re-generation even if an entry already exists. */
  regenerate?: boolean;
}

export interface UpdateTranslationRequest {
  language: string;
  content?: string;
  title?: string;
  safetyInstructions?: string;
  status?: TranslationStatus;
}

export interface GenerateAudioRequest {
  language: string;
  voice?: string;
  /** Regenerate/replace existing audio when true. */
  replace?: boolean;
}

export interface GenerateVariantRequest {
  language: string;
  kind: AiVariantKind;
}

export interface GenerateVariantResult {
  language: string;
  kind: AiVariantKind;
  content: string;
  updatedAt: string;
}
