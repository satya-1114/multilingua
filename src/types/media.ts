export type MediaKind = "document" | "image" | "video" | "audio";

export interface MediaAsset {
  id: string;
  name: string;
  kind: MediaKind;
  mimeType: string;
  sizeBytes: number;
  url: string;
  thumbnailUrl?: string;
  uploadedById: string;
  uploadedByName: string;
  favorite: boolean;
  tags: string[];
  createdAt: string;
}

export interface MediaListQuery {
  search?: string;
  kind?: MediaKind[];
  favorite?: boolean;
  page?: number;
  pageSize?: number;
}
