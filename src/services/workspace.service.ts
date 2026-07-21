import type { Workspace, WorkspaceUsage, WorkspaceBranding } from "@/types/workspace";
import { mockWorkspaces } from "@/lib/mock/platform";

const delay = <T>(v: T, ms = 220): Promise<T> =>
  new Promise((r) => setTimeout(() => r(v), ms));

const STORAGE_KEY = "platform.workspace.current";
const FAV_KEY = "platform.workspace.favorites";
const RECENT_KEY = "platform.workspace.recent";

let workspaces: Workspace[] = [...mockWorkspaces];
let currentId: string =
  (typeof localStorage !== "undefined" && localStorage.getItem(STORAGE_KEY)) ||
  workspaces.find((w) => w.isDefault)?.id ||
  workspaces[0].id;

function readSet(key: string): Set<string> {
  if (typeof localStorage === "undefined") return new Set();
  try {
    return new Set(JSON.parse(localStorage.getItem(key) || "[]"));
  } catch {
    return new Set();
  }
}
function writeSet(key: string, set: Set<string>): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(key, JSON.stringify([...set]));
}

export const workspaceService = {
  async list(): Promise<Workspace[]> {
    const favs = readSet(FAV_KEY);
    return delay(workspaces.map((w) => ({ ...w, isFavorite: favs.has(w.id) || w.isFavorite })));
  },
  async current(): Promise<Workspace> {
    const w = workspaces.find((x) => x.id === currentId) ?? workspaces[0];
    return delay(w);
  },
  async recent(): Promise<Workspace[]> {
    const ids: string[] = (() => {
      if (typeof localStorage === "undefined") return [];
      try { return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); } catch { return []; }
    })();
    const mapped = ids.map((id) => workspaces.find((w) => w.id === id)).filter(Boolean) as Workspace[];
    return delay(mapped.slice(0, 4));
  },
  async favorites(): Promise<Workspace[]> {
    const favs = readSet(FAV_KEY);
    return delay(workspaces.filter((w) => favs.has(w.id) || w.isFavorite));
  },
  async switchTo(id: string): Promise<Workspace> {
    const w = workspaces.find((x) => x.id === id);
    if (!w) throw new Error("Workspace not found");
    currentId = id;
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(STORAGE_KEY, id);
      try {
        const recent: string[] = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
        const next = [id, ...recent.filter((r) => r !== id)].slice(0, 6);
        localStorage.setItem(RECENT_KEY, JSON.stringify(next));
      } catch { /* noop */ }
    }
    return delay(w, 120);
  },
  async toggleFavorite(id: string): Promise<void> {
    const favs = readSet(FAV_KEY);
    if (favs.has(id)) favs.delete(id); else favs.add(id);
    writeSet(FAV_KEY, favs);
    return delay(undefined, 60);
  },
  async usage(id: string): Promise<WorkspaceUsage> {
    const w = workspaces.find((x) => x.id === id) ?? workspaces[0];
    return delay({
      storageUsedGb: w.storageUsedGb,
      storageQuotaGb: w.storageQuotaGb,
      apiUsedThisMonth: w.apiUsedThisMonth,
      apiQuotaMonthly: w.apiQuotaMonthly,
      seatsUsed: w.memberCount,
      seatsQuota: Math.round(w.memberCount * 1.4),
    });
  },
  async updateBranding(id: string, branding: WorkspaceBranding): Promise<void> {
    workspaces = workspaces.map((w) => (w.id === id ? { ...w, colorAccent: branding.primaryColor, logoUrl: branding.logoUrl } : w));
    return delay(undefined, 200);
  },
  async update(id: string, patch: Partial<Workspace>): Promise<Workspace> {
    workspaces = workspaces.map((w) => (w.id === id ? { ...w, ...patch } : w));
    return delay(workspaces.find((w) => w.id === id) as Workspace);
  },
};
