import type { AiGenerationRequest, AiGenerationResult, AiSuggestion, AiContentScores } from "@/types/ai";
import type { ApiResponse } from "@/types/api";
import { ok } from "@/types/api";
import { apiService } from "@/services/api.service";
import { environmentService } from "@/services/environment.service";
import { synthScores, synthSuggestions, fakeGeneratedContent } from "@/lib/mock/ai";

/**
 * AI content generation service.
 *
 * Calls the FastAPI `/api/v1/ai/generate` endpoint by default; falls back
 * to a mock generator only when `VITE_MOCK_MODE=true`. Provider selection
 * (Gemini / Ollama / Hugging Face / watsonx / OpenAI) happens on the
 * backend — the frontend never sees API keys.
 */
interface BackendGenerateDto {
  id: string;
  content: string;
  provider: string;
  model: string;
  tokens: number;
  responseTimeMs?: number;
  mode?: string;
  language?: string;
  cached?: boolean;
}

function buildBackendPrompt(request: AiGenerationRequest): string {
  const bits: string[] = [];
  if (request.objective) bits.push(`Objective: ${request.objective}`);
  if (request.audience) bits.push(`Audience: ${request.audience}`);
  if (request.channel) bits.push(`Channel: ${request.channel}`);
  if (request.wordLimit) bits.push(`Word limit: ~${request.wordLimit}`);
  if (request.keywords?.length) bits.push(`Keywords: ${request.keywords.join(", ")}`);
  if (request.callToAction) bits.push(`Call to action: ${request.callToAction}`);
  if (request.compliance?.length) bits.push(`Compliance: ${request.compliance.join(", ")}`);
  bits.push(`Content type: ${request.contentType}`);
  bits.push("");
  bits.push(request.prompt || `Draft a ${request.contentType.replace(/_/g, " ")} for our audience.`);
  if (request.seedContent) bits.push("\nExisting draft:\n" + request.seedContent);
  return bits.filter(Boolean).join("\n");
}

async function generate(
  request: AiGenerationRequest,
): Promise<ApiResponse<AiGenerationResult>> {
  if (environmentService.isAiMockEnabled()) return mockGenerate(request);
  const dto = await apiService.post<BackendGenerateDto>("/ai/generate", {
    prompt: buildBackendPrompt(request),
    mode: request.mode,
    tone: request.tone,
    language: request.language,
  });
  const content = dto.content ?? "";
  const words = content.trim().split(/\s+/).filter(Boolean).length;
  const suggestions: AiSuggestion[] = [];
  const scores: AiContentScores = synthScores(content.length);
  const result: AiGenerationResult = {
    id: dto.id || cryptoId("gen"),
    requestId: cryptoId("req"),
    contentType: request.contentType,
    mode: request.mode,
    tone: request.tone,
    language: request.language,
    content,
    characters: content.length,
    words,
    tokens: dto.tokens ?? 0,
    suggestions,
    scores,
    createdAt: new Date().toISOString(),
    model: dto.model ? `${dto.provider ?? "ai"}:${dto.model}` : "ai",
  };
  return ok(result);
}

async function mockGenerate(request: AiGenerationRequest): Promise<ApiResponse<AiGenerationResult>> {
  await delay(400);
  const content = fakeGeneratedContent(request.prompt, request.tone, request.language);
  const words = content.trim().split(/\s+/).filter(Boolean).length;
  return ok({
    id: cryptoId("gen"),
    requestId: cryptoId("req"),
    contentType: request.contentType,
    mode: request.mode,
    tone: request.tone,
    language: request.language,
    content,
    characters: content.length,
    words,
    tokens: Math.round(words * 1.35),
    suggestions: synthSuggestions(),
    scores: synthScores(),
    createdAt: new Date().toISOString(),
    model: "mock.multilingual.v1",
  });
}

async function regenerate(
  original: AiGenerationResult,
  overrides: Partial<AiGenerationRequest> = {},
): Promise<ApiResponse<AiGenerationResult>> {
  return generate({
    prompt: original.content,
    contentType: original.contentType,
    mode: overrides.mode ?? "rewrite",
    tone: overrides.tone ?? original.tone,
    language: overrides.language ?? original.language,
    ...overrides,
  });
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function cryptoId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID().slice(0, 8)}`;
  }
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

export interface AiProvidersInfo {
  providers: string[];
  supported: string[];
  default: string | null;
}

async function listProviders(): Promise<AiProvidersInfo> {
  if (environmentService.isAiMockEnabled()) return { providers: ["mock"], supported: ["gemini", "ollama", "huggingface", "watsonx", "openai"], default: "mock" };
  return apiService.get<AiProvidersInfo>("/ai/providers");
}

export interface WorkspaceAiSettingsDto {
  id?: string;
  workspaceId?: string;
  provider: string;
  model: string;
  apiKeyMasked?: string;
  hasApiKey?: boolean;
  baseUrl: string;
  projectId: string;
  temperature: number;
  maxTokens: number;
  autoReview: boolean;
  autoSave: boolean;
  defaultTone: string;
  defaultLanguage: string;
}

export interface WorkspaceAiSettingsInput extends Omit<WorkspaceAiSettingsDto, "id" | "workspaceId" | "apiKeyMasked" | "hasApiKey"> {
  apiKey?: string | null;
}

async function getWorkspaceSettings(): Promise<WorkspaceAiSettingsDto> {
  return apiService.get<WorkspaceAiSettingsDto>("/ai/workspace-settings");
}

async function saveWorkspaceSettings(input: WorkspaceAiSettingsInput): Promise<WorkspaceAiSettingsDto> {
  return apiService.put<WorkspaceAiSettingsDto>("/ai/workspace-settings", input);
}

async function testWorkspaceSettings(): Promise<{ ok: boolean; provider?: string; model?: string; error?: string }> {
  return apiService.post<{ ok: boolean; provider?: string; model?: string; error?: string }>("/ai/workspace-settings/test");
}

export const aiService = {
  generate,
  regenerate,
  listProviders,
  getWorkspaceSettings,
  saveWorkspaceSettings,
  testWorkspaceSettings,
};
