import type { MediaAsset, MediaKind, MediaListQuery } from "@/types/media";
import type { Paginated } from "@/types/common";
import { mockMedia } from "@/lib/mock/campaigns";

const NETWORK_DELAY = 180;
const delay = <T>(v: T, ms = NETWORK_DELAY) => new Promise<T>((r) => setTimeout(() => r(v), ms));

let store: MediaAsset[] = [...mockMedia];

function kindFromMime(mime: string): MediaKind {
  if (mime.startsWith("image/")) return "image";
  if (mime.startsWith("video/")) return "video";
  if (mime.startsWith("audio/")) return "audio";
  return "document";
}

export const mediaService = {
  async list(query: MediaListQuery = {}): Promise<Paginated<MediaAsset>> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 24;
    let items = [...store];
    if (query.search) {
      const s = query.search.toLowerCase();
      items = items.filter((m) => m.name.toLowerCase().includes(s));
    }
    if (query.kind?.length) items = items.filter((m) => query.kind!.includes(m.kind));
    if (query.favorite) items = items.filter((m) => m.favorite);
    items.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
    const start = (page - 1) * pageSize;
    return delay({
      items: items.slice(start, start + pageSize),
      total: items.length,
      page,
      pageSize,
    });
  },

  async upload(file: { name: string; type: string; size: number }, uploader = { id: "user-1", name: "You" }): Promise<MediaAsset> {
    const asset: MediaAsset = {
      id: `med-${crypto.randomUUID?.().slice(0, 8) ?? Math.random().toString(36).slice(2, 10)}`,
      name: file.name,
      kind: kindFromMime(file.type),
      mimeType: file.type,
      sizeBytes: file.size,
      url: "#",
      uploadedById: uploader.id,
      uploadedByName: uploader.name,
      favorite: false,
      tags: [],
      createdAt: new Date().toISOString(),
    };
    store = [asset, ...store];
    return delay(asset);
  },

  async toggleFavorite(id: string): Promise<void> {
    store = store.map((m) => (m.id === id ? { ...m, favorite: !m.favorite } : m));
    return delay(undefined);
  },

  async remove(id: string): Promise<void> {
    store = store.filter((m) => m.id !== id);
    return delay(undefined);
  },
};
