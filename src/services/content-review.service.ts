import type { AiContentScores, AiSuggestion } from "@/types/ai";
import type { ApiResponse } from "@/types/api";
import { ok } from "@/types/api";
import { synthScores, synthSuggestions } from "@/lib/mock/ai";

/**
 * Content review service — grammar, tone, compliance and scoring passes.
 * Kept as an abstraction over the future AI backend so UI never binds to a
 * concrete provider.
 */
async function review(content: string): Promise<
  ApiResponse<{ suggestions: AiSuggestion[]; scores: AiContentScores }>
> {
  await new Promise((r) => setTimeout(r, 250));
  return ok({ suggestions: synthSuggestions(), scores: synthScores(content.length) });
}

async function score(content: string): Promise<ApiResponse<AiContentScores>> {
  await new Promise((r) => setTimeout(r, 150));
  return ok(synthScores(content.length));
}

export const contentReviewService = { review, score };
