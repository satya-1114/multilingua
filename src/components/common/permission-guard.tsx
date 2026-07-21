import type { ReactNode } from "react";
import type { Permission, Role } from "@/constants/rbac";
import { usePermissions } from "@/hooks/use-permissions";

interface PermissionGuardProps {
  /** Grant access if the user has ANY of these permissions. */
  anyOf?: Permission[];
  /** Grant access if the user has ALL of these permissions. */
  allOf?: Permission[];
  /** Restrict to specific roles. */
  roles?: Role[];
  /** Content shown when the user is denied. Defaults to nothing. */
  fallback?: ReactNode;
  children: ReactNode;
}

/**
 * Declarative permission gate for JSX. Combine with route-level guards for
 * defense in depth — this hides UI, RBAC middleware protects the data.
 */
export function PermissionGuard({
  anyOf,
  allOf,
  roles,
  fallback = null,
  children,
}: PermissionGuardProps) {
  const { hasAnyPermission, hasAllPermissions, hasAnyRole } = usePermissions();

  const roleOk = !roles || roles.length === 0 || hasAnyRole(roles);
  const anyOk = !anyOf || anyOf.length === 0 || hasAnyPermission(anyOf);
  const allOk = !allOf || allOf.length === 0 || hasAllPermissions(allOf);

  if (!roleOk || !anyOk || !allOk) return <>{fallback}</>;
  return <>{children}</>;
}
