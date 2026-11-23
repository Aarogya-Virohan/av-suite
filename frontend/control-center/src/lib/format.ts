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

/**
 * Audit action codes as the backend writes them (platform_api.py,
 * platform_auth.py, create_platform_operator CLI): "organization.suspended",
 * and "organization.active" / "clinic.active" for activation (the backend builds
 * them from the new status). The mock uses the same codes.
 */
const ACTION_LABEL: Record<string, string> = {
  'organization.created': 'Organization created',
  'organization.updated': 'Organization updated',
  'organization.suspended': 'Organization suspended',
  'organization.active': 'Organization activated',
  'organization.merged': 'Organizations merged',
  'clinic.created': 'Branch added',
  'clinic.suspended': 'Clinic suspended',
  'clinic.active': 'Clinic activated',
  'entitlement.updated': 'Tool access changed',
  'operator.deactivated': 'Operator deactivated',
  'operator.reactivated': 'Operator reactivated',
  'operator.updated': 'Operator updated',
  'cli.operator.created': 'Operator created (CLI)',
  'auth.mfa_enrollment_started': 'Two-step setup started',
  'auth.mfa_verified': 'Operator signed in',
};

/** Actions the console writes, for the audit filter. */
export const AUDIT_ACTIONS = Object.keys(ACTION_LABEL);

export function auditActionLabel(action: string): string {
  return ACTION_LABEL[action] ?? action;
}

/** Product an audit row is about: the backend keeps it inside details.before / details.after. */
export function auditProductKey(details: Record<string, unknown>): string | null {
  const pick = (value: unknown): string | null =>
    value && typeof value === 'object' && typeof (value as { product_key?: unknown }).product_key === 'string'
      ? (value as { product_key: string }).product_key
      : null;
  if (typeof details.product_key === 'string') return details.product_key;
  return pick(details.after) ?? pick(details.before);
}

const USAGE_EVENT_LABEL: Record<string, string> = {
  login: 'Staff sign-in',
  patient_created: 'Patient added',
  appointment_created: 'Appointment booked',
  invoice_created: 'Invoice created',
  payment_recorded: 'Payment recorded',
  prescription_created: 'Prescription created',
  prescription_pdf: 'Prescription PDF',
  posture_report: 'Posture report',
  posture_pdf: 'Posture PDF',
  screening_assigned: 'Screening assigned',
  screening_completed: 'Screening completed',
};

export function usageEventLabel(eventType: string): string {
  return USAGE_EVENT_LABEL[eventType] ?? eventType;
}
