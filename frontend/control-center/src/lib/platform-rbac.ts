import type { OperatorRole } from './platform-api/types';

/**
 * Mirror of core/platform_rbac.py (6.3). The backend is the real check;
 * this only decides what the console shows.
 * confirm in S2: permission names.
 */
export const PLATFORM_PERMISSIONS = [
  'platform.organizations.read',
  'platform.organizations.manage',
  'platform.entitlements.manage',
  'platform.operators.manage',
  'platform.audit.read',
  'platform.usage.read',
] as const;

export type PlatformPermission = (typeof PLATFORM_PERMISSIONS)[number];

const READ_PERMISSIONS = PLATFORM_PERMISSIONS.filter((p) => p.endsWith('.read'));

/** Owner gets all; Support gets every `.read` (6.3, P-7). */
export const ROLE_PERMISSIONS: Record<OperatorRole, readonly PlatformPermission[]> = {
  owner: PLATFORM_PERMISSIONS,
  support: READ_PERMISSIONS,
};

export function roleHas(role: OperatorRole | null | undefined, permission: PlatformPermission): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role].includes(permission);
}
