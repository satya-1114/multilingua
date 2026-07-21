/**
 * Simple client-side favorites/pinned pages store used across the app.
 */
const KEY = "platform.favorites.pages";

export interface FavoritePage {
  to: string;
  title: string;
  addedAt: string;
}

function read(): FavoritePage[] {
  if (typeof localStorage === "undefined") return [];
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
}
function write(v: FavoritePage[]): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(KEY, JSON.stringify(v));
}

export const favoritesService = {
  list(): FavoritePage[] { return read(); },
  has(to: string): boolean { return read().some((f) => f.to === to); },
  toggle(page: Omit<FavoritePage, "addedAt">): FavoritePage[] {
    const cur = read();
    const exists = cur.some((f) => f.to === page.to);
    const next = exists ? cur.filter((f) => f.to !== page.to) : [{ ...page, addedAt: new Date().toISOString() }, ...cur].slice(0, 20);
    write(next);
    return next;
  },
  clear(): void { write([]); },
};
