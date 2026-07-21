import { ROLES, type Role } from "@/constants/rbac";

/**
 * Route-level RBAC map. Each entry gates a URL prefix behind a set of allowed
 * roles. Evaluated in order — the first matching prefix wins. Any path not
 * matched by a rule is available to every authenticated role.
 *
 * This mirrors backend RBAC (which remains authoritative) and prevents a
 * signed-in user from accessing pages by typing URLs manually.
 */
export interface RouteAccessRule {
  prefix: string;
  allow: Role[];
}

const ALL_AUTHENTICATED: Role[] = [
  ROLES.SUPER_ADMIN,
  ROLES.CAMPAIGN_MANAGER,
  ROLES.VOLUNTEER,
  ROLES.VIEWER,
];

const MANAGER_AND_ADMIN: Role[] = [ROLES.SUPER_ADMIN, ROLES.CAMPAIGN_MANAGER];
const ADMIN_ONLY: Role[] = [ROLES.SUPER_ADMIN];

export const ROUTE_ACCESS_RULES: RouteAccessRule[] = [
  // Platform administration — Super Admin only.
  { prefix: "/admin", allow: ADMIN_ONLY },
  { prefix: "/monitoring", allow: ADMIN_ONLY },
  { prefix: "/security", allow: ADMIN_ONLY },
  { prefix: "/jobs", allow: ADMIN_ONLY },
  { prefix: "/audit-logs", allow: ADMIN_ONLY },

  // Organization / workspace management — Campaign Manager + Super Admin.
  { prefix: "/organizations", allow: MANAGER_AND_ADMIN },
  { prefix: "/workspaces", allow: MANAGER_AND_ADMIN },
  { prefix: "/integrations", allow: MANAGER_AND_ADMIN },
  { prefix: "/automation", allow: MANAGER_AND_ADMIN },
  { prefix: "/communication", allow: MANAGER_AND_ADMIN },
  { prefix: "/campaigns/approvals", allow: MANAGER_AND_ADMIN },
  { prefix: "/campaigns/new", allow: MANAGER_AND_ADMIN },
  { prefix: "/analytics/builder", allow: MANAGER_AND_ADMIN },
  // Phase 6 — Platform analytics excludes Viewer per RBAC spec.
  { prefix: "/analytics", allow: [ROLES.SUPER_ADMIN, ROLES.CAMPAIGN_MANAGER, ROLES.VOLUNTEER] },
  { prefix: "/audience/new", allow: MANAGER_AND_ADMIN },
  { prefix: "/audience-groups", allow: MANAGER_AND_ADMIN },
  { prefix: "/volunteers", allow: MANAGER_AND_ADMIN },
  { prefix: "/my-tasks", allow: [ROLES.SUPER_ADMIN, ROLES.CAMPAIGN_MANAGER, ROLES.VOLUNTEER] },
  // Disaster management — read for all authenticated (viewer sees public shell),
  // manage/assign are enforced at the route/PermissionGuard level.
  { prefix: "/disasters/new", allow: MANAGER_AND_ADMIN },
  { prefix: "/disasters", allow: ALL_AUTHENTICATED },
];


/**
 * Returns true when the given role is permitted to access `pathname`.
 * Unknown paths default to allowed (already inside `_authenticated`).
 */
export function isRouteAllowed(pathname: string, role: Role | undefined | null): boolean {
  if (!role) return false;
  const rule = ROUTE_ACCESS_RULES.find((r) => pathname === r.prefix || pathname.startsWith(`${r.prefix}/`) || pathname.startsWith(r.prefix));
  const allowed = rule ? rule.allow : ALL_AUTHENTICATED;
  return allowed.includes(role);
}
