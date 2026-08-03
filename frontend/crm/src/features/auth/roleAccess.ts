import type { NavTab } from '@/components/layout/Sidebar';
import { UserRole } from './auth.types';

const ADMIN_ONLY_TABS = new Set<NavTab>(['analytics', 'recycle', 'settings']);

export const canAccessTab = (role: UserRole, tab: NavTab): boolean => {
  if (role === 'admin') {
    return true;
  }

  if (role === 'therapist') {
    return !ADMIN_ONLY_TABS.has(tab);
  }

  if (role === 'front_desk') {
    return ['dashboard', 'patients', 'appointments', 'billing', 'leads'].includes(tab);
  }

  return tab === 'dashboard';
};

export const getDefaultTabForRole = (role: UserRole): NavTab => {
  if (role === 'patient') {
    return 'dashboard';
  }

  return 'dashboard';
};

export const formatRole = (role: UserRole): string => {
  if (role === 'front_desk') {
    return 'Front Desk';
  }

  return role.charAt(0).toUpperCase() + role.slice(1);
};
