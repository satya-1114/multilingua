export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type JobKind =
  | "ai_generation"
  | "translation"
  | "bulk_delivery"
  | "audience_import"
  | "media_processing"
  | "export";

export interface JobRecord {
  id: string;
  kind: JobKind;
  title: string;
  status: JobStatus;
  progress: number;
  total?: number;
  processed?: number;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
  metadata?: Record<string, unknown>;
}
