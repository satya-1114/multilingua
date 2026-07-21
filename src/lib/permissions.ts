import { PERMISSIONS, ROLE_PERMISSIONS, type Permission, type Role } from "@/constants/rbac";

export function permissionsForRole(role: Role): Permission[] {
  return ROLE_PERMISSIONS[role] ?? [];
}

export function hasPermission(
  granted: Permission[] | undefined,
  required: Permission,
): boolean {
  if (!granted) return false;
  return granted.includes(required);
}

export function hasAnyPermission(
  granted: Permission[] | undefined,
  required: Permission[],
): boolean {
  if (!granted || required.length === 0) return false;
  return required.some((p) => granted.includes(p));
}

export function hasAllPermissions(
  granted: Permission[] | undefined,
  required: Permission[],
): boolean {
  if (!granted) return false;
  return required.every((p) => granted.includes(p));
}

export { PERMISSIONS };
