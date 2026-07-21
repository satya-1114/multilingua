/**
 * Backend-adapter for authentication and security-center endpoints.
 *
 * These call the FastAPI backend when `VITE_MOCK_MODE=false`. Consumers
 * can import from `@/api/auth.backend` directly, or use the shape-compatible
 * wrapper `authService` when integrating with existing UI.
 */

import { apiService } from "@/services/api.service";
import { tokenStorage } from "@/lib/token-storage";

export interface BackendUserDto {
  id: string;
  email: string;
  fullName: string;
  avatarUrl: string | null;
  status: "active" | "suspended";
  roles: string[];
  emailVerified: boolean;
  defaultWorkspaceId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface BackendTokenPair {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresAt: string;
  sessionId?: string;
}

interface LoginPayload {
  email: string;
  password: string;
  rememberMe?: boolean;
  deviceId?: string;
}

interface RegisterPayload {
  email: string;
  password: string;
  fullName: string;
}

function storeTokens(tokens: BackendTokenPair, remember: boolean) {
  const expiryEpoch = Math.floor(new Date(tokens.expiresAt).getTime() / 1000);
  tokenStorage.setAccessToken(tokens.accessToken, expiryEpoch);
  tokenStorage.setRefreshToken(tokens.refreshToken, remember);
}

function deviceIdFor(): string {
  const KEY = "app.deviceId";
  const existing = typeof window !== "undefined" ? window.localStorage.getItem(KEY) : null;
  if (existing) return existing;
  const id = crypto.randomUUID();
  if (typeof window !== "undefined") window.localStorage.setItem(KEY, id);
  return id;
}

export const authBackend = {
  async register(payload: RegisterPayload) {
    const res = await apiService.post<{ user: BackendUserDto; token: BackendTokenPair; verificationToken?: string }>(
      "/auth/register",
      payload,
    );
    storeTokens(res.token, false);
    return res;
  },

  async login(payload: LoginPayload) {
    const res = await apiService.post<{ user: BackendUserDto; token: BackendTokenPair }>("/auth/login", {
      ...payload,
      deviceId: payload.deviceId ?? deviceIdFor(),
    });
    storeTokens(res.token, !!payload.rememberMe);
    return res;
  },

  async refresh() {
    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) return null;
    const tokens = await apiService.post<BackendTokenPair>("/auth/refresh", { refreshToken });
    storeTokens(tokens, tokenStorage.isRemembered?.() ?? false);
    return tokens;
  },

  async me() {
    return apiService.get<BackendUserDto>("/auth/me");
  },

  async logout() {
    const refreshToken = tokenStorage.getRefreshToken();
    if (refreshToken) {
      try {
        await apiService.post("/auth/logout", { refreshToken });
      } catch {
        /* Ignore — always clear locally. */
      }
    }
    tokenStorage.clear();
  },

  async logoutAll() {
    await apiService.post<{ revoked: number }>("/auth/logout-all");
    tokenStorage.clear();
  },

  forgotPassword: (email: string) => apiService.post<{ delivered: boolean; token?: string }>("/auth/forgot-password", { email }),
  resetPassword: (token: string, password: string) => apiService.post<{ reset: boolean }>("/auth/reset-password", { token, password }),
  changePassword: (currentPassword: string, newPassword: string) =>
    apiService.post<{ changed: boolean }>("/auth/change-password", { currentPassword, newPassword }),
  verifyEmail: (token: string) => apiService.post<{ verified: boolean; user: BackendUserDto }>("/auth/verify-email", { token }),
  resendVerification: () => apiService.post<{ delivered: boolean; token?: string }>("/auth/resend-verification"),
  requestOtp: (email: string) => apiService.post<{ delivered: boolean; code?: string }>("/auth/request-otp", { email }),
  verifyOtp: (email: string, code: string) => apiService.post<{ verified: boolean }>("/auth/verify-otp", { email, code }),
  passwordStrength: (password: string) =>
    apiService.get<{ score: number }>("/auth/password-strength", { params: { password } }),
};

export interface SessionDto {
  id: string;
  ipAddress: string | null;
  userAgent: string | null;
  createdAt: string;
  expiresAt: string;
}

export interface DeviceDto {
  id: string;
  deviceId: string;
  label: string;
  type: string;
  browser: string | null;
  operatingSystem: string | null;
  trusted: boolean;
  lastSeenAt: string | null;
}

export interface LoginHistoryEntry {
  id: string;
  success: boolean;
  reason: string | null;
  ipAddress: string | null;
  userAgent: string | null;
  createdAt: string;
}

export interface SecurityAlertDto {
  id: string;
  event: string;
  severity: "info" | "warning" | "critical";
  ipAddress: string;
  detail: string;
  createdAt: string;
}

export interface SecurityScoreDto {
  score: number;
  grade: "A" | "B" | "C" | "D";
  checks: Array<{ key: string; passed: boolean; weight: number; value?: number }>;
  deviceCount: number;
  activeSessions: number;
}

export interface AccountStatusDto {
  active: boolean;
  emailVerified: boolean;
  locked: boolean;
  lockedUntil: string | null;
  failedAttempts: number;
}

export const securityBackend = {
  overview: () =>
    apiService.get<{
      score: SecurityScoreDto;
      account: AccountStatusDto;
      sessions: SessionDto[];
      devices: DeviceDto[];
      recentLogins: LoginHistoryEntry[];
      alerts: SecurityAlertDto[];
    }>("/security/overview"),
  sessions: () => apiService.get<SessionDto[]>("/security/sessions"),
  revokeSession: (id: string) => apiService.post<{ revoked: boolean }>(`/security/sessions/${id}/revoke`),
  revokeAllSessions: () => apiService.post<{ revoked: number }>("/security/sessions/revoke-all"),
  devices: () => apiService.get<DeviceDto[]>("/security/devices"),
  trustDevice: (id: string, trusted = true) =>
    apiService.post<{ deviceId: string; trusted: boolean }>(`/security/devices/${id}/trust`, undefined, {
      params: { trusted },
    }),
  removeDevice: (id: string) => apiService.delete<{ removed: boolean }>(`/security/devices/${id}`),
  logins: (limit = 25) =>
    apiService.get<{ recent: LoginHistoryEntry[]; failedLast24h: number }>("/security/logins", { params: { limit } }),
  alerts: (limit = 25) => apiService.get<SecurityAlertDto[]>("/security/alerts", { params: { limit } }),
  status: () => apiService.get<AccountStatusDto>("/security/status"),
  score: () => apiService.get<SecurityScoreDto>("/security/score"),
  passwordPolicy: () =>
    apiService.get<{
      minLength: number;
      maxLength: number;
      requireUppercase: boolean;
      requireLowercase: boolean;
      requireDigit: boolean;
      requireSymbol: boolean;
      historySize: number;
      maxAgeDays: number;
    }>("/security/password-policy"),
  mfaFactors: () => apiService.get<Array<{ id: string; type: string; label: string; verified: boolean }>>("/security/mfa/factors"),
  mfaEnroll: (factorType: "totp" | "sms" | "email", label = "") =>
    apiService.post<{ factorId: string; secret?: string }>("/security/mfa/enroll", { factorType, label }),
  mfaVerify: (factorId: string, code: string) =>
    apiService.post<{ verified: boolean }>("/security/mfa/verify", { factorId, code }),
  mfaDisable: (factorId: string) => apiService.delete<{ disabled: boolean }>(`/security/mfa/factors/${factorId}`),
  mfaRecoveryCodes: () => apiService.post<{ codes: string[] }>("/security/mfa/recovery-codes"),
};
