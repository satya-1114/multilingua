import type { JobRecord, JobStatus } from "@/types/jobs";
import type { ApiPaginatedResponse, ApiResponse } from "@/types/api";
import { ok, paginate } from "@/types/api";
import { mockJobs } from "@/lib/mock/ai";

let store: JobRecord[] = [...mockJobs];

export interface JobsQuery {
  page?: number;
  pageSize?: number;
  status?: JobStatus | "all";
}

async function list(q: JobsQuery = {}): Promise<ApiPaginatedResponse<JobRecord>> {
  const page = q.page ?? 1;
  const pageSize = q.pageSize ?? 20;
  let items = [...store];
  if (q.status && q.status !== "all") items = items.filter((j) => j.status === q.status);
  items.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  const start = (page - 1) * pageSize;
  return paginate(items.slice(start, start + pageSize), page, pageSize, items.length);
}

async function retry(id: string): Promise<ApiResponse<JobRecord | null>> {
  store = store.map((j) =>
    j.id === id
      ? {
          ...j,
          status: "queued",
          progress: 0,
          processed: 0,
          errorMessage: undefined,
          updatedAt: new Date().toISOString(),
        }
      : j,
  );
  return ok(store.find((j) => j.id === id) ?? null);
}

async function cancel(id: string): Promise<ApiResponse<JobRecord | null>> {
  store = store.map((j) =>
    j.id === id ? { ...j, status: "cancelled", updatedAt: new Date().toISOString() } : j,
  );
  return ok(store.find((j) => j.id === id) ?? null);
}

export const jobsService = { list, retry, cancel };
