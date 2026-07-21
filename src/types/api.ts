/**
 * Central API envelope contracts.
 *
 * These types mirror the shape the future FastAPI backend will return so
 * frontend services, mocks and hooks all share a single response schema.
 */

export interface ApiMetadata {
  requestId?: string;
  timestamp?: string;
  version?: string;
  durationMs?: number;
}

export interface ApiPagination {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasMore: boolean;
}

export interface ApiError {
  code: string;
  message: string;
  field?: string;
  details?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  success: true;
  data: T;
  meta?: ApiMetadata;
}

export interface ApiPaginatedResponse<T> {
  success: true;
  data: T[];
  pagination: ApiPagination;
  meta?: ApiMetadata;
}

export interface ApiFailureResponse {
  success: false;
  error: ApiError;
  meta?: ApiMetadata;
}

export type ApiResult<T> = ApiResponse<T> | ApiFailureResponse;

export function ok<T>(data: T, meta?: ApiMetadata): ApiResponse<T> {
  return { success: true, data, meta };
}

export function paginate<T>(
  items: T[],
  page: number,
  pageSize: number,
  total: number,
  meta?: ApiMetadata,
): ApiPaginatedResponse<T> {
  return {
    success: true,
    data: items,
    pagination: {
      page,
      pageSize,
      total,
      totalPages: Math.max(1, Math.ceil(total / pageSize)),
      hasMore: page * pageSize < total,
    },
    meta,
  };
}
