import type { AccountStatus, OperatorRole, OrganizationType } from './platform-api/types';
import type { BadgeTone } from '@/components/ui/brand';

const IST = 'Asia/Kolkata';

export function formatDate(value: string | null | undefined): string {
  if (!value) return '-';
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: IST }).format(new Date(value));
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-';
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: IST,
  }).format(new Date(value));
}

/** "3 h ago", "2 d ago". Falls back to the date after 30 days. */
export function formatRelative(value: string | null | undefined, now: number = Date.now()): string {
  if (!value) return 'Never';
  const diff = now - new Date(value).getTime();
  const minutes = Math.round(diff / 60_000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days <= 30) return `${days} d ago`;
  return formatDate(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-IN').format(value);
}

export const ORGANIZATION_TYPE_LABEL: Record<OrganizationType, string> = {
  individual: 'Solo physio',
  clinic: 'Single clinic',
  chain: 'Chain',
  franchise: 'Franchise',
  hospital: 'Hospital',
  government: 'Government',
  partner_platform: 'Partner platform',
};

export const OPERATOR_ROLE_LABEL: Record<OperatorRole, string> = {
  owner: 'Owner',
  support: 'Support',
};

export const STATUS_LABEL: Record<AccountStatus, string> = { active: 'Active', suspended: 'Suspended' };
export const STATUS_TONE: Record<AccountStatus, BadgeTone> = { active: 'ok', suspended: 'danger' };

/** "organization.suspend" -> "Organization suspended". */
const ACTION_LABEL: Record<string, string> = {
  'organization.create': 'Organization created',
  'organization.update': 'Organization updated',
  'organization.suspend': 'Organization suspended',
  'organization.activate': 'Organization activated',
  'organization.merge': 'Organizations merged',
  'clinic.create': 'Branch added',
  'clinic.suspend': 'Clinic suspended',
  'clinic.activate': 'Clinic activated',
  'entitlement.update': 'Tool access changed',
  'operator.create': 'Operator created',
  'operator.update': 'Operator updated',
};

/** Actions the console writes, for the audit filter. */
export const AUDIT_ACTIONS = Object.keys(ACTION_LABEL);

export function auditActionLabel(action: string): string {
  return ACTION_LABEL[action] ?? action;
}
