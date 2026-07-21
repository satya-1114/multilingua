import { useAuth } from "@/contexts/auth-context";
import type { Permission } from "@/constants/rbac";

/** Convenience hook — thin wrapper around the auth context permission helpers. */
export function usePermissions() {
  const { user, hasPermission, hasAnyPermission, hasAllPermissions, hasRole, hasAnyRole } =
    useAuth();
  return {
    permissions: (user?.permissions ?? []) as Permission[],
    role: user?.role ?? null,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    hasAnyRole,
  };
}
