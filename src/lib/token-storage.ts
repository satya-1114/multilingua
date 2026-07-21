/**
 * Secure token storage.
 *
 * Strategy:
 *  - Access token: in-memory only. Never persisted. Cleared on tab close
 *    or manual logout; refreshed transparently via the refresh token.
 *  - Refresh token: stored in sessionStorage (per-tab, cleared on close),
 *    or in a browser-managed persistent store when "Remember me" is set.
 *    A production backend should upgrade this to an httpOnly, Secure,
 *    SameSite=Strict cookie set by the auth API — the app code does not
 *    change when that happens.
 *
 * LocalStorage is intentionally NOT used for access tokens (XSS blast
 * radius). The `app.remembered` flag persists across tabs so the app knows
 * whether to attempt a refresh on cold start.
 */

const REFRESH_KEY = "app.refresh";
const REMEMBER_KEY = "app.remembered";

let accessToken: string | null = null;
let accessTokenExpiresAt: number | null = null;
const listeners = new Set<(token: string | null) => void>();

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export const tokenStorage = {
  getAccessToken(): string | null {
    return accessToken;
  },

  getAccessTokenExpiry(): number | null {
    return accessTokenExpiresAt;
  },

  setAccessToken(token: string | null, expiresAt: number | null = null): void {
    accessToken = token;
    accessTokenExpiresAt = expiresAt;
    listeners.forEach((l) => l(token));
  },

  onAccessTokenChange(listener: (token: string | null) => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },

  getRefreshToken(): string | null {
    if (!isBrowser()) return null;
    return (
      window.sessionStorage.getItem(REFRESH_KEY) ??
      window.localStorage.getItem(REFRESH_KEY)
    );
  },

  setRefreshToken(token: string | null, remember: boolean): void {
    if (!isBrowser()) return;
    window.sessionStorage.removeItem(REFRESH_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
    if (!token) {
      window.localStorage.removeItem(REMEMBER_KEY);
      return;
    }
    if (remember) {
      window.localStorage.setItem(REFRESH_KEY, token);
      window.localStorage.setItem(REMEMBER_KEY, "1");
    } else {
      window.sessionStorage.setItem(REFRESH_KEY, token);
    }
  },

  isRemembered(): boolean {
    if (!isBrowser()) return false;
    return window.localStorage.getItem(REMEMBER_KEY) === "1";
  },

  clear(): void {
    accessToken = null;
    accessTokenExpiresAt = null;
    if (isBrowser()) {
      window.sessionStorage.removeItem(REFRESH_KEY);
      window.localStorage.removeItem(REFRESH_KEY);
      window.localStorage.removeItem(REMEMBER_KEY);
    }
    listeners.forEach((l) => l(null));
  },
};

export function isTokenExpired(expiresAt: number | null, skewSeconds = 30): boolean {
  if (!expiresAt) return true;
  return Date.now() / 1000 >= expiresAt - skewSeconds;
}
