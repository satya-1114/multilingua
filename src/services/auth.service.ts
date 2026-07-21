/**
 * Authentication service — real FastAPI backend implementation.
 *
 * Every method calls the backend at `${VITE_API_BASE_URL}/auth/*` through
 * the shared HTTP client (which handles the `{ success, data, meta }`
 * envelope, error translation, retries, and token attachment). No mock
 * users, no fabricated tokens, no artificial delays.
 */

import type {
  AuthTokens,
  AuthUser,
  LoginRequest,
  OtpVerificationRequest,
  RegisterRequest,
  ResetPasswordRequest,
} from "@/types/auth";
import { ROLES, ROLE_PERMISSIONS, type Role } from "@/constants/rbac";
import { apiService } from "@/services/api.service";
import { tokenStorage } from "@/lib/token-storage";

// ---------------------------------------------------------------------------
// Backend DTOs (mirror backend/app/api/v1/auth.py _user_dto and token payload)
// ---------------------------------------------------------------------------

interface BackendUserDto {
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

interface BackendTokenDto {
  accessToken: string;
  refreshToken: string;
  tokenType?: string;
  /** ISO 8601 timestamp. */
  expiresAt: string;
  sessionId?: string;
}

interface AuthEnvelope {
  user: BackendUserDto;
  token: BackendTokenDto;
  verificationToken?: string;
}

// ---------------------------------------------------------------------------
// Mapping helpers
// ---------------------------------------------------------------------------

function mapRole(roles: string[] | undefined | null): Role {
  const known = new Set<string>(Object.values(ROLES));
  if (roles) {
    for (const r of roles) {
      if (known.has(r)) return r as Role;
    }
  }
  return ROLES.VIEWER;
}

function splitName(full: string | null | undefined): { firstName: string; lastName: string } {
  const trimmed = (full ?? "").trim();
  if (!trimmed) return { firstName: "", lastName: "" };
  const parts = trimmed.split(/\s+/);
  if (parts.length === 1) return { firstName: parts[0], lastName: "" };
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") };
}

function toAuthUser(dto: BackendUserDto): AuthUser {
  const role = mapRole(dto.roles);
  const { firstName, lastName } = splitName(dto.fullName);
  return {
    id: dto.id,
    email: dto.email,
    firstName,
    lastName,
    fullName: dto.fullName ?? "",
    avatarUrl: dto.avatarUrl ?? undefined,
    role,
    permissions: ROLE_PERMISSIONS[role],
    organization: {
      id: dto.defaultWorkspaceId ?? "",
      name: "",
      type: "",
    },
    timezone: typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "UTC",
    locale: typeof navigator !== "undefined" ? navigator.language : "en",
    emailVerified: dto.emailVerified,
    twoFactorEnabled: false,
    createdAt: dto.createdAt,
    lastLoginAt: dto.updatedAt,
  };
}

function toAuthTokens(dto: BackendTokenDto): AuthTokens {
  const expiresAt = Math.floor(new Date(dto.expiresAt).getTime() / 1000);
  return {
    accessToken: dto.accessToken,
    refreshToken: dto.refreshToken,
    expiresAt: Number.isFinite(expiresAt) ? expiresAt : Math.floor(Date.now() / 1000) + 900,
  };
}

function storeTokens(tokens: AuthTokens, remember: boolean) {
  tokenStorage.setAccessToken(tokens.accessToken, tokens.expiresAt);
  tokenStorage.setRefreshToken(tokens.refreshToken, remember);
}

function deviceId(): string {
  const KEY = "app.deviceId";
  if (typeof window === "undefined") return "server";
  const existing = window.localStorage.getItem(KEY);
  if (existing) return existing;
  const id = crypto.randomUUID();
  window.localStorage.setItem(KEY, id);
  return id;
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const authService = {
  async login(input: LoginRequest): Promise<{ user: AuthUser; tokens: AuthTokens }> {
    const res = await apiService.post<AuthEnvelope>("/auth/login", {
      email: input.email,
      password: input.password,
      rememberMe: !!input.rememberMe,
      deviceId: deviceId(),
    });
    const tokens = toAuthTokens(res.token);
    storeTokens(tokens, !!input.rememberMe);
    return { user: toAuthUser(res.user), tokens };
  },

  async register(input: RegisterRequest): Promise<{ user: AuthUser; tokens: AuthTokens }> {
    if (!input.acceptTerms || !input.acceptPrivacy) {
      throw new Error("You must accept the terms and privacy policy");
    }
    const res = await apiService.post<AuthEnvelope>("/auth/register", {
      email: input.email,
      password: input.password,
      fullName: input.fullName,
      phone: input.phone,
      role: input.role,
      profile: {
        organizationName: input.organizationName,
        organizationType: input.organizationType,
        officeAddress: input.officeAddress,
        designation: input.designation,
        languagesKnown: input.languagesKnown,
        skills: input.skills,
        currentLocation: input.currentLocation,
        availability: input.availability,
      },
    });
    const tokens = toAuthTokens(res.token);
    storeTokens(tokens, false);
    return { user: toAuthUser(res.user), tokens };
  },

  async refresh(): Promise<AuthTokens | null> {
    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) return null;
    const res = await apiService.post<BackendTokenDto>("/auth/refresh", { refreshToken });
    const tokens = toAuthTokens(res);
    storeTokens(tokens, tokenStorage.isRemembered());
    return tokens;
  },

  async me(): Promise<AuthUser | null> {
    if (!tokenStorage.getAccessToken()) return null;
    const dto = await apiService.get<BackendUserDto>("/auth/me");
    return toAuthUser(dto);
  },

  async logout(): Promise<void> {
    const refreshToken = tokenStorage.getRefreshToken();
    if (refreshToken) {
      try {
        await apiService.post("/auth/logout", { refreshToken });
      } catch {
        // Always clear locally, even if the revoke call fails.
      }
    }
    tokenStorage.clear();
  },

  async requestPasswordReset(email: string): Promise<{ email: string }> {
    if (!email) throw new Error("Email is required");
    await apiService.post<{ delivered: boolean; token?: string }>("/auth/forgot-password", { email });
    return { email };
  },

  async verifyOtp(input: OtpVerificationRequest): Promise<{ token: string }> {
    if (!/^\d{6}$/.test(input.code)) {
      throw new Error("Enter the 6-digit code sent to your email");
    }
    const res = await apiService.post<{ verified: boolean; token?: string }>("/auth/verify-otp", {
      email: input.email,
      code: input.code,
    });
    return { token: res.token ?? "" };
  },

  async requestOtp(email: string): Promise<{ delivered: boolean }> {
    const res = await apiService.post<{ delivered: boolean; code?: string }>("/auth/request-otp", { email });
    return { delivered: !!res.delivered };
  },

  async resetPassword(input: ResetPasswordRequest): Promise<{ ok: true }> {
    if (!input.token || input.password.length < 8) {
      throw new Error("Invalid reset request");
    }
    await apiService.post<{ reset: boolean }>("/auth/reset-password", {
      token: input.token,
      password: input.password,
    });
    return { ok: true } as const;
  },

  async verifyEmail(token: string): Promise<{ ok: true }> {
    if (!token) throw new Error("Verification token is required");
    await apiService.post<{ verified: boolean }>("/auth/verify-email", { token });
    return { ok: true } as const;
  },

  async resendEmailVerification(email: string): Promise<{ email: string }> {
    await apiService.post<{ delivered: boolean; token?: string }>("/auth/resend-verification");
    return { email };
  },

  async changePassword(current: string, next: string): Promise<{ ok: true }> {
    if (!current || next.length < 8) throw new Error("Invalid password change request");
    await apiService.post<{ changed: boolean }>("/auth/change-password", {
      currentPassword: current,
      newPassword: next,
    });
    return { ok: true } as const;
  },

  /**
   * OAuth2 Password Flow token endpoint — form-encoded. Only used when the
   * caller needs a raw bearer token (e.g. integrating with Swagger-style
   * tooling). Standard app login uses `login()`.
   */
  async token(username: string, password: string): Promise<{ accessToken: string; tokenType: string }> {
    const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "")
      ?? "http://localhost:8000/api/v1";
    const body = new URLSearchParams({ username, password, grant_type: "password" });
    const res = await fetch(`${base}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || `Token request failed with status ${res.status}`);
    }
    const json = (await res.json()) as { access_token: string; token_type: string };
    return { accessToken: json.access_token, tokenType: json.token_type };
  },
};
