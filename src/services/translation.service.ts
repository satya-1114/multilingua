// ============================================================================
// Translation service
//
// Two surfaces:
//   • Legacy AI free-text translation (translate/batch) — retained for the
//     /translation AI workspace page. Kept as mock (no backend endpoint).
//   • Multilingual Content Platform — real HTTP calls into the FastAPI
//     `/api/v1/translations` router added in Phase 5.3.
//
// Follows the same thin-facade shape used by disaster.service and
// volunteer.service (apiService + httpClient for paginated envelopes).
// ============================================================================

import { apiService } from "./api.service";
import { httpClient } from "@/api/client/http-client";
import type { ApiResponse } from "@/types/api";
import { ok } from "@/types/api";
import { LANGUAGES } from "@/constants/india";
import type { Paginated } from "@/types/common";
import type {
  BatchTranslationRequest,
  BatchTranslationResult,
  EntityTranslation,
  EntityTranslationInput,
  EntityTranslationUpdate,
  TranslationJob,
  TranslationJobInput,
  TranslationJobListQuery,
  TranslationListQuery,
  TranslationLocale,
  TranslationLocaleInput,
  TranslationLocaleUpdate,
  TranslationQualityScores,
  TranslationRequest,
  TranslationResult,
} from "@/types/translation";

// ─────────────────────────────────────────────────────────────────────────────
// Legacy AI translation workspace (mocked)
// ─────────────────────────────────────────────────────────────────────────────
async function translate(
  req: TranslationRequest,
): Promise<ApiResponse<TranslationResult>> {
  const data = await apiService.post<any>("/translation", {
    text: req.content,
    sourceLanguage: req.sourceLanguage,
    targetLanguage: req.targetLanguage,
    workspaceId: req.workspaceId,
  });

  const result: TranslationResult = {
    id: crypto.randomUUID(),

    sourceLanguage: data.sourceLanguage,
    targetLanguage: data.targetLanguage,

    sourceContent: data.sourceText,
    translatedContent: data.translatedText,

    scores: {
      accuracy: Math.round((data.quality ?? 1) * 100),
      readability: Math.round((data.confidence ?? 1) * 100),
      tone: 95,
      consistency: 95,
      grammar: 95,
      accessibility: 95,
    },

    createdAt: new Date().toISOString(),
    createdBy: data.provider ?? "gemini",
    characters: data.translatedText.length,
  };

  return ok(result);
}

async function batch(
  req: BatchTranslationRequest,
): Promise<ApiResponse<BatchTranslationResult>> {
  const entries = await Promise.all(
    req.targetLanguages.map(async (target) => {
      const res = await translate({
        sourceLanguage: req.sourceLanguage,
        targetLanguage: target,
        content: req.content,
        workspaceId: req.workspaceId,
      });

      return res.data;
    }),
  );

  return ok({
    id: crypto.randomUUID(),
    sourceLanguage: req.sourceLanguage,
    entries,
    createdAt: new Date().toISOString(),
  });
}
// ─────────────────────────────────────────────────────────────────────────────
// Multilingual Content Platform
// ─────────────────────────────────────────────────────────────────────────────

const BASE = "/translations";

type Params = Record<string, string | number | boolean | undefined>;

async function listTranslations(
  query: TranslationListQuery = {},
): Promise<Paginated<EntityTranslation>> {
  const env = await httpClient.request<EntityTranslation[]>({
    method: "GET",
    path: BASE,
    params: query as Params,
  });
  const items = Array.isArray(env.data) ? env.data : [];
  const pg = env.pagination;
  return {
    items,
    total: pg?.total ?? items.length,
    page: pg?.page ?? query.page ?? 1,
    pageSize: pg?.pageSize ?? query.pageSize ?? items.length,
  };
}

function getTranslation(id: string): Promise<EntityTranslation> {
  return apiService.get<EntityTranslation>(`${BASE}/${id}`);
}

function createTranslation(
  input: EntityTranslationInput,
): Promise<EntityTranslation> {
  return apiService.post<EntityTranslation>(BASE, input);
}

function updateTranslation(
  id: string,
  patch: EntityTranslationUpdate,
): Promise<EntityTranslation> {
  return apiService.patch<EntityTranslation>(`${BASE}/${id}`, patch);
}

function deleteTranslation(id: string): Promise<{ id: string; deleted: boolean }> {
  return apiService.delete<{ id: string; deleted: boolean }>(`${BASE}/${id}`);
}

function reviewTranslation(id: string): Promise<EntityTranslation> {
  return apiService.post<EntityTranslation>(`${BASE}/${id}/review`);
}

function rejectTranslation(id: string): Promise<EntityTranslation> {
  return apiService.post<EntityTranslation>(`${BASE}/${id}/reject`);
}

function publishTranslation(id: string): Promise<EntityTranslation> {
  return apiService.post<EntityTranslation>(`${BASE}/${id}/publish`);
}

function getEntityTranslations(
  entityType: string,
  entityId: string,
  locale?: string,
): Promise<EntityTranslation[]> {
  return apiService.get<EntityTranslation[]>(
    `${BASE}/entity/${entityType}/${entityId}`,
    locale ? { params: { locale } } : undefined,
  );
}

// ── Jobs ────────────────────────────────────────────────────────────────────

async function listJobs(
  query: TranslationJobListQuery = {},
): Promise<Paginated<TranslationJob>> {
  const env = await httpClient.request<TranslationJob[]>({
    method: "GET",
    path: `${BASE}/jobs`,
    params: query as Params,
  });
  const items = Array.isArray(env.data) ? env.data : [];
  const pg = env.pagination;
  return {
    items,
    total: pg?.total ?? items.length,
    page: pg?.page ?? query.page ?? 1,
    pageSize: pg?.pageSize ?? query.pageSize ?? items.length,
  };
}

function getJob(id: string): Promise<TranslationJob> {
  return apiService.get<TranslationJob>(`${BASE}/jobs/${id}`);
}

function createJob(input: TranslationJobInput): Promise<TranslationJob> {
  return apiService.post<TranslationJob>(`${BASE}/jobs`, input);
}

function startJob(id: string): Promise<TranslationJob> {
  return apiService.post<TranslationJob>(`${BASE}/jobs/${id}/start`);
}

function completeJob(
  id: string,
  metadata?: Record<string, unknown>,
): Promise<TranslationJob> {
  return apiService.post<TranslationJob>(
    `${BASE}/jobs/${id}/complete`,
    metadata ? { metadata } : {},
  );
}

function failJob(id: string, error?: string): Promise<TranslationJob> {
  return apiService.post<TranslationJob>(
    `${BASE}/jobs/${id}/fail`,
    error ? { error } : {},
  );
}

function cancelJob(id: string): Promise<TranslationJob> {
  return apiService.post<TranslationJob>(`${BASE}/jobs/${id}/cancel`);
}

// ── Locales ─────────────────────────────────────────────────────────────────

function listLocales(enabledOnly = false): Promise<TranslationLocale[]> {
  return apiService.get<TranslationLocale[]>(`${BASE}/locales`, {
    params: enabledOnly ? { enabledOnly: true } : undefined,
  });
}

function createLocale(
  input: TranslationLocaleInput,
): Promise<TranslationLocale> {
  return apiService.post<TranslationLocale>(`${BASE}/locales`, input);
}

function updateLocaleMeta(
  locale: string,
  patch: TranslationLocaleUpdate,
): Promise<TranslationLocale> {
  return apiService.patch<TranslationLocale>(
    `${BASE}/locales/${locale}`,
    patch,
  );
}

function enableLocale(locale: string): Promise<TranslationLocale> {
  return apiService.post<TranslationLocale>(`${BASE}/locales/${locale}/enable`);
}

function disableLocale(locale: string): Promise<TranslationLocale> {
  return apiService.post<TranslationLocale>(
    `${BASE}/locales/${locale}/disable`,
  );
}

function setDefaultLocale(locale: string): Promise<TranslationLocale> {
  return apiService.post<TranslationLocale>(
    `${BASE}/locales/${locale}/set-default`,
  );
}

export const translationService = {
  // Legacy AI workspace
  translate,
  batch,
  // Translations
  listTranslations,
  getTranslation,
  createTranslation,
  updateTranslation,
  deleteTranslation,
  reviewTranslation,
  rejectTranslation,
  publishTranslation,
  getEntityTranslations,
  // Jobs
  listJobs,
  getJob,
  createJob,
  startJob,
  completeJob,
  failJob,
  cancelJob,
  // Locales
  listLocales,
  createLocale,
  updateLocaleMeta,
  enableLocale,
  disableLocale,
  setDefaultLocale,
};
