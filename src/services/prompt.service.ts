import type { PromptCategory, PromptTemplate } from "@/types/ai";
import type { ApiPaginatedResponse, ApiResponse } from "@/types/api";
import { ok, paginate } from "@/types/api";
import { apiService } from "@/services/api.service";
import { environmentService } from "@/services/environment.service";
import { mockPrompts } from "@/lib/mock/ai";

let mockStore: PromptTemplate[] = [...mockPrompts];

interface BackendPromptDto {
  id: string;
  name: string;
  title?: string;
  description: string;
  category: string;
  body: string;
  variables: string[] | Array<{ key?: string; name?: string }>;
  tags: string[];
  favorite: boolean;
  isSystem?: boolean;
  usageCount: number;
  createdBy?: string;
  createdAt: string;
  updatedAt: string;
}

function fromBackend(dto: BackendPromptDto): PromptTemplate {
  const vars = Array.isArray(dto.variables)
    ? dto.variables.map((v) => (typeof v === "string" ? v : v.key ?? v.name ?? "")).filter(Boolean)
    : [];
  return {
    id: dto.id,
    title: dto.title || dto.name,
    description: dto.description || "",
    category: (dto.category as PromptCategory) || "general",
    body: dto.body,
    tags: dto.tags || [],
    variables: vars,
    favorite: dto.favorite,
    createdBy: dto.createdBy || "system",
    createdAt: dto.createdAt,
    updatedAt: dto.updatedAt,
    usageCount: dto.usageCount ?? 0,
  };
}

export interface PromptQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  category?: PromptCategory | "all";
  favoritesOnly?: boolean;
  tags?: string[];
}

async function list(
  query: PromptQuery = {},
): Promise<ApiPaginatedResponse<PromptTemplate>> {
  if (!environmentService.isAiMockEnabled()) {
    const res = await apiService.get<{ items: BackendPromptDto[]; total: number; page: number; pageSize: number }>(
      "/ai/prompts",
      {
        params: {
          page: query.page ?? 1,
          page_size: query.pageSize ?? 20,
          search: query.search,
          category: query.category && query.category !== "all" ? query.category : undefined,
          favorites_only: query.favoritesOnly ? "true" : undefined,
        },
      },
    );
    const items = (res.items || []).map(fromBackend);
    return paginate(items, res.page ?? 1, res.pageSize ?? items.length, res.total ?? items.length);
  }
  const page = query.page ?? 1;
  const pageSize = query.pageSize ?? 20;
  let filtered = [...mockStore];
  if (query.category && query.category !== "all") {
    filtered = filtered.filter((p) => p.category === query.category);
  }
  if (query.favoritesOnly) filtered = filtered.filter((p) => p.favorite);
  if (query.search) {
    const q = query.search.toLowerCase();
    filtered = filtered.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.tags.some((t) => t.toLowerCase().includes(q)),
    );
  }
  if (query.tags?.length) {
    filtered = filtered.filter((p) => query.tags!.every((t) => p.tags.includes(t)));
  }
  const start = (page - 1) * pageSize;
  const items = filtered.slice(start, start + pageSize);
  return paginate(items, page, pageSize, filtered.length);
}

async function get(id: string): Promise<ApiResponse<PromptTemplate | null>> {
  if (environmentService.isAiMockEnabled()) return ok(mockStore.find((p) => p.id === id) ?? null);
  try {
    const dto = await apiService.get<BackendPromptDto>(`/ai/prompts/${id}`);
    return ok(fromBackend(dto));
  } catch {
    return ok(null);
  }
}

async function create(
  input: Omit<PromptTemplate, "id" | "createdAt" | "updatedAt" | "usageCount">,
): Promise<ApiResponse<PromptTemplate>> {
  if (!environmentService.isAiMockEnabled()) {
    const dto = await apiService.post<BackendPromptDto>("/ai/prompts", {
      name: input.title,
      category: input.category,
      description: input.description,
      body: input.body,
      variables: input.variables,
      tags: input.tags,
      favorite: input.favorite,
    });
    return ok(fromBackend(dto));
  }
  const now = new Date().toISOString();
  const prompt: PromptTemplate = {
    ...input,
    id: `prompt-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: now,
    updatedAt: now,
    usageCount: 0,
  };
  mockStore = [prompt, ...mockStore];
  return ok(prompt);
}

async function update(
  id: string,
  patch: Partial<PromptTemplate>,
): Promise<ApiResponse<PromptTemplate | null>> {
  if (!environmentService.isAiMockEnabled()) {
    const current = (await get(id)).data;
    if (!current) return ok(null);
    const merged = { ...current, ...patch };
    const dto = await apiService.patch<BackendPromptDto>(`/ai/prompts/${id}`, {
      name: merged.title,
      category: merged.category,
      description: merged.description,
      body: merged.body,
      variables: merged.variables,
      tags: merged.tags,
      favorite: merged.favorite,
    });
    return ok(fromBackend(dto));
  }
  mockStore = mockStore.map((p) =>
    p.id === id ? { ...p, ...patch, updatedAt: new Date().toISOString() } : p,
  );
  return get(id);
}

async function remove(id: string): Promise<ApiResponse<boolean>> {
  if (!environmentService.isAiMockEnabled()) {
    const res = await apiService.delete<{ deleted: boolean }>(`/ai/prompts/${id}`);
    return ok(!!res.deleted);
  }
  const before = mockStore.length;
  mockStore = mockStore.filter((p) => p.id !== id);
  return ok(mockStore.length < before);
}

async function duplicate(id: string): Promise<ApiResponse<PromptTemplate | null>> {
  if (!environmentService.isAiMockEnabled()) {
    const dto = await apiService.post<BackendPromptDto>(`/ai/prompts/${id}/duplicate`);
    return ok(fromBackend(dto));
  }
  const source = mockStore.find((p) => p.id === id);
  if (!source) return ok(null);
  const copy: PromptTemplate = {
    ...source,
    id: `prompt-${Math.random().toString(36).slice(2, 8)}`,
    title: `${source.title} (copy)`,
    favorite: false,
    usageCount: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  mockStore = [copy, ...mockStore];
  return ok(copy);
}

async function toggleFavorite(
  id: string,
): Promise<ApiResponse<PromptTemplate | null>> {
  if (!environmentService.isAiMockEnabled()) {
    const dto = await apiService.post<BackendPromptDto>(`/ai/prompts/${id}/favorite`);
    return ok(fromBackend(dto));
  }
  const current = mockStore.find((p) => p.id === id);
  if (!current) return ok(null);
  return update(id, { favorite: !current.favorite });
}

async function markUsed(id: string): Promise<void> {
  if (environmentService.isAiMockEnabled()) return;
  try {
    await apiService.post(`/ai/prompts/${id}/use`);
  } catch {
    /* best-effort */
  }
}

export const promptService = {
  list,
  get,
  create,
  update,
  remove,
  duplicate,
  toggleFavorite,
  markUsed,
};
