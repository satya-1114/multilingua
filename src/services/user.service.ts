import type { AuthUser, LoginHistoryEntry } from "@/types/auth";
import { apiService } from "./api.service";

interface BackendLoginHistoryEntry {
  id: string;
  success: boolean;
  reason: string | null;
  ipAddress: string | null;
  userAgent: string | null;
  createdAt: string;
}

function mapLoginHistory(entry: BackendLoginHistoryEntry): LoginHistoryEntry {
  return {
    id: entry.id,
    ipAddress: entry.ipAddress ?? "",
    location: "",
    device: "",
    browser: entry.userAgent ?? "",
    status: entry.success ? "success" : "failed",
    timestamp: entry.createdAt,
  };
}
export interface PlatformUser {
  id: string;
  email: string;
  fullName: string;
  avatarUrl: string | null;
  status: string;
  roles: string[];
  createdAt: string;
  updatedAt: string;
}

export interface UpdatePlatformUserInput {
  fullName?: string;
  avatarUrl?: string;
  status?: string;
  roles?: string[];
}
export const userService = {
  async getProfile(): Promise<unknown> {
    return apiService.get("/auth/me");
  },

  async getUsers(): Promise<PlatformUser[]> {
  return apiService.get<PlatformUser[]>("/users");
},

async updateUser(
  userId: string,
  patch: UpdatePlatformUserInput,
): Promise<PlatformUser> {
  return apiService.patch<PlatformUser>(
    `/users/${userId}`,
    patch,
  );
},

  async getLoginHistory(): Promise<LoginHistoryEntry[]> {
    try {
      const res = await apiService.get<{ recent: BackendLoginHistoryEntry[] } | BackendLoginHistoryEntry[]>(
        "/security/logins",
        { params: { limit: 25 } },
      );
      const items = Array.isArray(res) ? res : res?.recent ?? [];
      return items.map(mapLoginHistory);
    } catch {
      return [];
    }
  },

async updateProfile(patch: Partial<AuthUser>): Promise<Partial<AuthUser>> {
  const me = await apiService.get<{ id: string }>("/users/me");

  return apiService.patch<Partial<AuthUser>>(
    `/users/${me.id}`,
    patch,
  );
},

  async enableTwoFactor(): Promise<{ ok: true }> {
    throw new Error("2FA not implemented");
  },

  async disableTwoFactor(): Promise<{ ok: true }> {
    throw new Error("2FA not implemented");
  },
};

