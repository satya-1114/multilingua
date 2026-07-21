import type { ApiResponse } from "@/types/api";
import { ok } from "@/types/api";

export type UploadKind = "image" | "document" | "csv" | "video";
export type UploadStatus = "queued" | "uploading" | "completed" | "failed" | "cancelled";

export interface UploadItem {
  id: string;
  file: File;
  kind: UploadKind;
  status: UploadStatus;
  progress: number;
  errorMessage?: string;
  previewUrl?: string;
  startedAt?: string;
  completedAt?: string;
}

export interface UploadValidationRules {
  maxSizeMB?: number;
  allowedTypes?: string[];
}

const DEFAULT_RULES: Record<UploadKind, UploadValidationRules> = {
  image: { maxSizeMB: 10, allowedTypes: ["image/jpeg", "image/png", "image/webp", "image/svg+xml"] },
  document: {
    maxSizeMB: 25,
    allowedTypes: ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
  },
  csv: { maxSizeMB: 25, allowedTypes: ["text/csv", "application/vnd.ms-excel"] },
  video: { maxSizeMB: 200, allowedTypes: ["video/mp4", "video/webm"] },
};

export function validateFile(file: File, kind: UploadKind, rules?: UploadValidationRules) {
  const merged = { ...DEFAULT_RULES[kind], ...rules };
  if (merged.maxSizeMB && file.size > merged.maxSizeMB * 1024 * 1024) {
    return `File exceeds ${merged.maxSizeMB} MB`;
  }
  if (merged.allowedTypes && merged.allowedTypes.length && !merged.allowedTypes.includes(file.type)) {
    return `Type ${file.type || "unknown"} is not allowed`;
  }
  return null;
}

async function upload(
  file: File,
  onProgress?: (progress: number) => void,
): Promise<ApiResponse<{ url: string; id: string }>> {
  for (let p = 10; p <= 100; p += 15) {
    await new Promise((r) => setTimeout(r, 120));
    onProgress?.(Math.min(p, 100));
  }
  return ok({
    id: `upload-${Math.random().toString(36).slice(2, 8)}`,
    url: URL.createObjectURL(file),
  });
}

export const uploadService = { upload, validate: validateFile };
