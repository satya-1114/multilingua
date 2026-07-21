import type { AiHistoryEntry } from "@/types/ai";
import type { ApiPaginatedResponse, ApiResponse } from "@/types/api";
import { ok, paginate } from "@/types/api";
import { apiService } from "@/services/api.service";
import { environmentService } from "@/services/environment.service";
import { mockAiHistory } from "@/lib/mock/ai";
import { synthScores } from "@/lib/mock/ai";

let mockStore: AiHistoryEntry[] = [...mockAiHistory];

interface BackendHistoryDto {
  id: string;
  title?: string;
  prompt: string;
  content: string;
  preview?: string;
  provider?: string;
  model?: string;
  mode?: string;
  language?: string;
  tokens?: number;
  promptTokens?: number;
  completionTokens?: number;
  responseTimeMs?: number;
  status?: string;
  contentType?: string;
  createdBy?: string;
  createdAt: string;
  updatedAt?: string;
  versions?: number;
}

function fromBackend(dto: BackendHistoryDto): AiHistoryEntry {
  return {
    id: dto.id,
    title: dto.title || dto.prompt.slice(0, 80),
    contentType: (dto.contentType as AiHistoryEntry["contentType"]) || "custom",
    mode: (dto.mode as AiHistoryEntry["mode"]) || "create",
    language: dto.language || "en",
    preview: dto.preview || (dto.content || "").slice(0, 180),
    content: dto.content || "",
    scores: synthScores(dto.responseTimeMs ?? 0),
    createdBy: dto.createdBy || "",
    createdAt: dto.createdAt,
    versions: dto.versions ?? 1,
  };
}

export interface HistoryQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  language?: string;
  provider?: string;
}

async function list(q: HistoryQuery = {}): Promise<ApiPaginatedResponse<AiHistoryEntry>> {
  if (!environmentService.isAiMockEnabled()) {
    const res = await apiService.get<{ items: BackendHistoryDto[]; total: number; page: number; pageSize: number }>(
      "/ai/history",
      {
        params: {
          page: q.page ?? 1,
          page_size: q.pageSize ?? 20,
          search: q.search,
          language: q.language,
          provider: q.provider,
        },
      },
    );
    const items = (res.items || []).map(fromBackend);
    return paginate(items, res.page ?? 1, res.pageSize ?? items.length, res.total ?? items.length);
  }
  const page = q.page ?? 1;
  const pageSize = q.pageSize ?? 20;
  let items = [...mockStore];
  if (q.language) items = items.filter((i) => i.language === q.language);
  if (q.search) {
    const s = q.search.toLowerCase();
    items = items.filter((i) => i.title.toLowerCase().includes(s));
  }
  const start = (page - 1) * pageSize;
  return paginate(items.slice(start, start + pageSize), page, pageSize, items.length);
}

async function remove(id: string): Promise<ApiResponse<boolean>> {
  if (!environmentService.isAiMockEnabled()) {
    const res = await apiService.delete<{ deleted: boolean }>(`/ai/history/${id}`);
    return ok(!!res.deleted);
  }
  const before = mockStore.length;
  mockStore = mockStore.filter((i) => i.id !== id);
  return ok(mockStore.length < before);
}

export const historyService = { list, remove };
