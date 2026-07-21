import { apiService } from "@/services/api.service";
import type {
  GenerateAudioRequest,
  GenerateTranslationRequest,
  GenerateVariantRequest,
  GenerateVariantResult,
  MultilingualContent,
  MultilingualParentType,
  TranslationEntry,
  UpdateTranslationRequest,
} from "@/types/multilingual";

/**
 * Multilingual content service.
 *
 * Thin facade over the existing `apiService`. There is intentionally NO
 * separate HTTP client, translation engine, TTS pipeline or media uploader
 * in the frontend — those responsibilities belong to `translationService`,
 * the AI gateway, and the existing media pipeline on the backend.
 *
 * Every endpoint is scoped by parent (`campaign` | `disaster`) so the same
 * REST surface serves Campaigns, Disaster Alerts, and any future entity
 * that opts in.
 *
 * Backend contract: `docs/BACKEND-MULTILINGUAL.md`.
 */

function base(parent: MultilingualParentType, id: string) {
  const root = parent === "campaign" ? "campaigns" : "disasters";
  return `/v1/${root}/${id}/multilingual`;
}

export const multilingualService = {
  /** Fetch the multilingual bundle for an entity. */
  get(parent: MultilingualParentType, id: string) {
    return apiService.get<MultilingualContent>(base(parent, id));
  },

  /** Trigger AI translation for one or more target languages. */
  generate(
    parent: MultilingualParentType,
    id: string,
    body: GenerateTranslationRequest,
  ) {
    return apiService.post<MultilingualContent>(`${base(parent, id)}/translate`, body);
  },

  /** Regenerate a single language's translation, discarding manual edits. */
  regenerate(parent: MultilingualParentType, id: string, language: string) {
    return apiService.post<TranslationEntry>(
      `${base(parent, id)}/translate/${language}/regenerate`,
    );
  },

  /** Manually edit or publish a translation entry. */
  update(
    parent: MultilingualParentType,
    id: string,
    body: UpdateTranslationRequest,
  ) {
    return apiService.patch<TranslationEntry>(
      `${base(parent, id)}/translations/${body.language}`,
      body,
    );
  },

  /** Delete a translation entry (source language cannot be removed). */
  remove(parent: MultilingualParentType, id: string, language: string) {
    return apiService.delete<void>(`${base(parent, id)}/translations/${language}`);
  },

  /** Generate or replace TTS audio for a language. */
  generateAudio(
    parent: MultilingualParentType,
    id: string,
    body: GenerateAudioRequest,
  ) {
    return apiService.post<TranslationEntry>(
      `${base(parent, id)}/translations/${body.language}/audio`,
      body,
    );
  },

  /** Delete the audio asset for a language (keeps the translation text). */
  removeAudio(parent: MultilingualParentType, id: string, language: string) {
    return apiService.delete<void>(
      `${base(parent, id)}/translations/${language}/audio`,
    );
  },

  /** Generate an AI content variant (summary, sms, poster, …) for a language. */
  generateVariant(
    parent: MultilingualParentType,
    id: string,
    body: GenerateVariantRequest,
  ) {
    return apiService.post<GenerateVariantResult>(
      `${base(parent, id)}/translations/${body.language}/variants`,
      body,
    );
  },
};
