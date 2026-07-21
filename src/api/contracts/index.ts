/**
 * Standardized enterprise API contracts. Every service response and DTO
 * flows through these envelopes so UI code never depends on backend shape.
 */

export interface ApiMetadata {
  requestId: string;
  timestamp: string;
  version: string;
  durationMs?: number;
  traceId?: string;
}

export interface ApiPagination {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasMore: boolean;
}

export interface ApiCursorPagination {
  cursor: string | null;
  nextCursor: string | null;
  pageSize: number;
  hasMore: boolean;
}

export interface ApiValidationError {
  field: string;
  code: string;
  message: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  status: number;
  details?: Record<string, unknown>;
  validation?: ApiValidationError[];
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  errors?: Record<string, string[]>;
}

export interface ApiResponse<T> {
  success: true;
  data: T;
  meta: ApiMetadata;
}

export interface ApiListResponse<T> {
  success: true;
  data: T[];
  pagination: ApiPagination;
  meta: ApiMetadata;
}

export interface ApiCursorResponse<T> {
  success: true;
  data: T[];
  pagination: ApiCursorPagination;
  meta: ApiMetadata;
}

export interface ApiFailure {
  success: false;
  error: ApiErrorBody;
  meta: ApiMetadata;
}

export type ApiResult<T> = ApiResponse<T> | ApiFailure;

export interface RequestContext {
  workspaceId?: string;
  userId?: string;
  locale?: string;
  timezone?: string;
  correlationId?: string;
}

export interface ResponseContext {
  cached: boolean;
  etag?: string;
  fromMock: boolean;
  latencyMs: number;
}

function nowMeta(): ApiMetadata {
  return {
    requestId: `req_${Math.random().toString(36).slice(2, 12)}`,
    timestamp: new Date().toISOString(),
    version: "1.0",
  };
}

export function ok<T>(data: T, meta: Partial<ApiMetadata> = {}): ApiResponse<T> {
  return { success: true, data, meta: { ...nowMeta(), ...meta } };
}

export function list<T>(
  data: T[],
  pagination: Partial<ApiPagination> & { page: number; pageSize: number; total: number },
  meta: Partial<ApiMetadata> = {},
): ApiListResponse<T> {
  const totalPages = Math.max(1, Math.ceil(pagination.total / pagination.pageSize));
  return {
    success: true,
    data,
    pagination: {
      ...pagination,
      totalPages,
      hasMore: pagination.page < totalPages,
    },
    meta: { ...nowMeta(), ...meta },
  };
}

export function fail(code: string, message: string, status = 400, details?: Record<string, unknown>): ApiFailure {
  return {
    success: false,
    error: { code, message, status, details },
    meta: nowMeta(),
  };
}
