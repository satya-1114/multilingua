import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type {
  AuthUser,
  LoginRequest,
  RegisterRequest,
} from "@/types/auth";
import type { Permission, Role } from "@/constants/rbac";
import { authService } from "@/services/auth.service";
import {
  hasAllPermissions,
  hasAnyPermission,
  hasPermission,
} from "@/lib/permissions";
import {
  isTokenExpired,
  tokenStorage,
} from "@/lib/token-storage";

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (input: LoginRequest) => Promise<AuthUser>;
  register: (input: RegisterRequest) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  hasRole: (role: Role) => boolean;
  hasAnyRole: (roles: Role[]) => boolean;
  hasPermission: (permission: Permission) => boolean;
  hasAnyPermission: (permissions: Permission[]) => boolean;
  hasAllPermissions: (permissions: Permission[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// Poll the access token expiry every 30s and refresh proactively.
const REFRESH_INTERVAL_MS = 30_000;
// Refresh when the access token has this many seconds left.
const REFRESH_WINDOW_SECONDS = 90;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshingRef = useRef<Promise<void> | null>(null);

  const performRefresh = useCallback(async () => {
    if (refreshingRef.current) return refreshingRef.current;
    const job = (async () => {
      try {
        const tokens = await authService.refresh();
        if (!tokens) {
          setUser(null);
          tokenStorage.clear();
          return;
        }
        const me = await authService.me();
        setUser(me);
      } catch {
        setUser(null);
        tokenStorage.clear();
      } finally {
        refreshingRef.current = null;
      }
    })();
    refreshingRef.current = job;
    return job;
  }, []);

  // Bootstrap: attempt to restore session from refresh token on cold start.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (tokenStorage.getRefreshToken()) {
        await performRefresh();
      }
      if (!cancelled) setIsLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [performRefresh]);

  // Auto-refresh loop.
  useEffect(() => {
    if (!user) return;
    const timer = window.setInterval(() => {
      const expiresAt = tokenStorage.getAccessTokenExpiry();
      if (isTokenExpired(expiresAt, REFRESH_WINDOW_SECONDS)) {
        void performRefresh();
      }
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [user, performRefresh]);

  // Cross-tab sign-out: if refresh token disappears, sign out here too.
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === "app.refresh" && e.newValue === null) {
        tokenStorage.clear();
        setUser(null);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const login = useCallback(async (input: LoginRequest) => {
    const { user: authed } = await authService.login(input);
    setUser(authed);
    return authed;
  }, []);

  const register = useCallback(async (input: RegisterRequest) => {
    const { user: authed } = await authService.register(input);
    setUser(authed);
    return authed;
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
      refresh: performRefresh,
      hasRole: (role) => user?.role === role,
      hasAnyRole: (roles) => (user ? roles.includes(user.role) : false),
      hasPermission: (p) => hasPermission(user?.permissions, p),
      hasAnyPermission: (perms) => hasAnyPermission(user?.permissions, perms),
      hasAllPermissions: (perms) => hasAllPermissions(user?.permissions, perms),
    }),
    [user, isLoading, login, register, logout, performRefresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
