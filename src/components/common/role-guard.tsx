import type { ReactNode } from "react";
import type { Role } from "@/constants/rbac";
import { useAuth } from "@/contexts/auth-context";
import { ForbiddenView } from "@/components/common/forbidden-view";

interface RoleGuardProps {
  /** Roles allowed to see the children. If empty/undefined, all roles pass. */
  allow?: Role[];
  /** Roles explicitly denied (evaluated after `allow`). */
  deny?: Role[];
  /**
   * When the user is not allowed:
   *  - "hide"     → render `fallback` (default `null`).
   *  - "redirect" → navigate to `/forbidden` (route-level protection).
   */
  mode?: "hide" | "redirect";
  fallback?: ReactNode;
  children: ReactNode;
}

/**
 * Reusable role-based visibility / access guard.
 *
 * Composes with the auth context (`useAuth`) — the single source of truth for
 * the current user's role — so it can be dropped anywhere in the tree without
 * duplicating role checks.
 *
 *   <RoleGuard allow={[ROLES.CAMPAIGN_MANAGER, ROLES.SUPER_ADMIN]}>
 *     ...manager-only UI...
 *   </RoleGuard>
 *
 *   <RoleGuard allow={[ROLES.SUPER_ADMIN]} mode="redirect">
 *     <AdminOnlyPage />
 *   </RoleGuard>
 */
export function RoleGuard({
  allow,
  deny,
  mode = "hide",
  fallback = null,
  children,
}: RoleGuardProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;

  const role = user?.role;
  const allowOk = !allow || allow.length === 0 || (role ? allow.includes(role) : false);
  const denyOk = !deny || deny.length === 0 || (role ? !deny.includes(role) : true);
  const permitted = allowOk && denyOk;

  if (permitted) return <>{children}</>;
  if (mode === "redirect") return <ForbiddenView />;
  return <>{fallback}</>;
}
