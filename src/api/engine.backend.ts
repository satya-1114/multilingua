/**
 * Backend-adapter for AI, Translation, Communication, and Monitoring APIs.
 *
 * Live when `VITE_MOCK_MODE=false`. Import from `@/api/backend` (aggregate)
 * or here directly.
 */

import { apiService } from "@/services/api.service";

/* ------------------------------------------------------------------ AI  */

export interface AiGenerationDto {
  id: string;
  prompt: string;
  provider: string;
  model: string;
  tokens: number;
  content: string;
  cached: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface AiReviewDto {
  compliance?: { risk?: string; issues?: unknown[]; suggestions?: string[] };
  sentiment?: { sentiment?: string; tone?: string; formality?: string; confidence?: number };
  readability?: { grade?: number; score?: number; level?: string };
  inclusive?: { issues?: unknown[] };
  qualityScore: number;
}

export const aiBackend = {
  providers: () => apiService.get<{ providers: string[] }>("/ai/providers"),
  generate: (input: {
    prompt: string;
    mode?: string;
    tone?: string;
    language?: string;
    workspaceId?: string;
  }) => apiService.post<AiGenerationDto>("/ai/generate", input),
  review: (content: string, checks?: string[], provider?: string) =>
    apiService.post<AiReviewDto>("/ai/review", { content, checks, provider }),
  render: (body: string, variables: Record<string, unknown>) =>
    apiService.post<{ rendered: string; missing: string[] }>("/ai/render", { body, variables }),
  prompts: () => apiService.get<{ items: unknown[] }>("/ai/prompts"),
  history: (params?: { page?: number; pageSize?: number; search?: string }) =>
    apiService.get<{ items: AiGenerationDto[]; total: number }>("/ai/history", { params }),
  deleteHistory: (id: string) => apiService.delete<{ deleted: boolean }>(`/ai/history/${id}`),
  stream: async function* (input: { prompt: string; mode?: string }): AsyncGenerator<string> {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ""}/ai/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    if (!response.body) return;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      yield decoder.decode(value);
    }
  },
};

/* ------------------------------------------------------------------ Translation */

export interface TranslationDto {
  sourceLanguage: string;
  targetLanguage: string;
  sourceText: string;
  translatedText: string;
  quality: number;
  confidence: number;
  provider: string;
  cached: boolean;
}

export const translationBackend = {
  languages: () => apiService.get<Array<{ code: string; name: string }>>("/translation/languages"),
  detect: (text: string) => apiService.post<{ language: string }>("/translation/detect", { text }),
  translate: (input: {
    text: string;
    targetLanguage: string;
    sourceLanguage?: string;
    workspaceId?: string;
  }) => apiService.post<TranslationDto>("/translation", input),
  batch: (input: {
    items: string[];
    targetLanguage: string;
    sourceLanguage?: string;
    concurrency?: number;
  }) => apiService.post<{ results: TranslationDto[]; count: number }>("/translation/batch", input),
  compare: (input: { text: string; targetLanguage: string; sourceLanguage?: string }) =>
    apiService.post<{ candidates: TranslationDto[]; recommended: TranslationDto }>("/translation/compare", input),
  addGlossaryTerm: (term: string, translations: Record<string, string>) =>
    apiService.post<{ term: string; translations: Record<string, string> }>("/translation/glossary", {
      term, translations,
    }),
  history: () => apiService.get<TranslationDto[]>("/translation/history"),
};

/* ------------------------------------------------------------------ Communication */

export interface DeliveryDto {
  id: string;
  campaignId: string;
  channel: string;
  status: string;
  scheduledAt: string | null;
  attempts: number;
  createdAt: string;
  updatedAt: string;
}

export const communicationBackend = {
  channels: () => apiService.get<{ items: unknown[]; total: number }>("/communication/channels"),
  deliveries: (params?: { page?: number; pageSize?: number }) =>
    apiService.get<{ items: DeliveryDto[]; total: number }>("/communication/delivery", { params }),
  schedule: (input: { campaignId: string; channel: string; scheduledAt?: string; priority?: number }) =>
    apiService.post<DeliveryDto>("/communication/schedule", input),
  retryDelivery: (id: string) => apiService.post<{ queued: boolean }>(`/communication/delivery/${id}/retry`),
  retryPolicies: () => apiService.get<unknown[]>("/communication/retry-policies"),
};

/* ------------------------------------------------------------------ Monitoring */

export interface QueueSnapshot {
  workers: Array<{ name: string; active: number; reserved: number; scheduled: number; pool: unknown }>;
  queues: Array<{ name: string; pending: number; running: number }>;
}

export const monitoringBackend = {
  health: () => apiService.get<{ status: string; at: string; checks: unknown[] }>("/monitoring/health"),
  queues: () => apiService.get<QueueSnapshot>("/monitoring/queues"),
  deliveryStats: () =>
    apiService.get<{ deliveries: Record<string, number>; recipients: Record<string, number> }>(
      "/monitoring/deliveries",
    ),
  providers: () =>
    apiService.get<Array<{ channel: string; provider: string; configured: boolean }>>("/monitoring/providers"),
  cancelJob: (taskId: string) =>
    apiService.post<{ cancelled: boolean; taskId?: string; error?: string }>(`/monitoring/queues/${taskId}/cancel`),
};
