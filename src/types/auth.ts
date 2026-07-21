import type { Permission, Role } from "@/constants/rbac";

export interface AuthUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  fullName: string;
  phone?: string;
  avatarUrl?: string;
  role: Role;
  permissions: Permission[];
  organization: {
    id: string;
    name: string;
    type: string;
  };
  timezone: string;
  locale: string;
  emailVerified: boolean;
  twoFactorEnabled: boolean;
  createdAt: string;
  lastLoginAt?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  /** Unix seconds. */
  expiresAt: number;
}

export interface LoginRequest {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterRequest {
  /** One of the registration-selectable roles (Viewer, Volunteer, Campaign Manager). */
  role: "viewer" | "volunteer" | "campaign_manager";
  fullName: string;
  email: string;
  phone: string;
  password: string;
  acceptTerms: boolean;
  acceptPrivacy: boolean;

  // Campaign Manager profile
  organizationName?: string;
  organizationType?: string;
  officeAddress?: string;
  designation?: string;

  // Volunteer profile
  languagesKnown?: string[];
  skills?: string[];
  currentLocation?: string;
  availability?: string;
}

export interface OtpVerificationRequest {
  email: string;
  code: string;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}

export interface LoginHistoryEntry {
  id: string;
  ipAddress: string;
  location: string;
  device: string;
  browser: string;
  status: "success" | "failed";
  timestamp: string;
}
