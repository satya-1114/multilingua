import type { AiDraft } from "@/types/ai";
import type { ApiPaginatedResponse, ApiResponse } from "@/types/api";
import { ok, paginate } from "@/types/api";
import { mockAiDrafts } from "@/lib/mock/ai";

let store: AiDraft[] = [...mockAiDrafts];

export interface DraftQuery {
  page?: number;
  pageSize?: number;
  archived?: boolean;
  pinnedOnly?: boolean;
  search?: string;
}

async function list(q: DraftQuery = {}): Promise<ApiPaginatedResponse<AiDraft>> {
  const page = q.page ?? 1;
  const pageSize = q.pageSize ?? 20;
  let items = [...store];
  items = items.filter((d) => d.archived === Boolean(q.archived));
  if (q.pinnedOnly) items = items.filter((d) => d.pinned);
  if (q.search) {
    const s = q.search.toLowerCase();
    items = items.filter((d) => d.title.toLowerCase().includes(s));
  }
  items.sort(
    (a, b) =>
      Number(b.pinned) - Number(a.pinned) ||
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );
  const start = (page - 1) * pageSize;
  return paginate(items.slice(start, start + pageSize), page, pageSize, items.length);
}

async function upsert(
  input: Partial<AiDraft> & { id?: string; title: string; content: string; language: string },
): Promise<ApiResponse<AiDraft>> {
  const now = new Date().toISOString();
  if (input.id) {
    const existing = store.find((d) => d.id === input.id);
    if (existing) {
      const next: AiDraft = { ...existing, ...input, updatedAt: now } as AiDraft;
      store = store.map((d) => (d.id === next.id ? next : d));
      return ok(next);
    }
  }
  const draft: AiDraft = {
    id: `draft-${Math.random().toString(36).slice(2, 8)}`,
    title: input.title,
    content: input.content,
    language: input.language,
    contentType: input.contentType ?? "custom",
    updatedAt: now,
    pinned: input.pinned ?? false,
    archived: false,
    autoSaved: input.autoSaved ?? true,
  };
  store = [draft, ...store];
  return ok(draft);
}

async function archive(id: string): Promise<ApiResponse<boolean>> {
  store = store.map((d) => (d.id === id ? { ...d, archived: true } : d));
  return ok(true);
}

async function pin(id: string, pinned: boolean): Promise<ApiResponse<boolean>> {
  store = store.map((d) => (d.id === id ? { ...d, pinned } : d));
  return ok(true);
}

async function remove(id: string): Promise<ApiResponse<boolean>> {
  const before = store.length;
  store = store.filter((d) => d.id !== id);
  return ok(store.length < before);
}

export const draftService = { list, upsert, archive, pin, remove };
