import type { components } from '../../types/schema';

export type LostReason = components['schemas']['LeadLostReason'];

/* The founders' own list and words (Decisions.md D-026). Order as they gave it. */
export const LOST_REASONS: { value: LostReason; label: string }[] = [
  { value: 'denied', label: 'Denied' },
  { value: 'better_price', label: 'Better price' },
  { value: 'asked_for_discount', label: 'Asked for discount' },
  { value: 'offer', label: 'Offer' },
  { value: 'call_not_picked', label: 'Call not picked' },
  { value: 'other', label: 'Other' },
];

export const LOST_REMARK_MAX = 500;

export function lostReasonLabel(value: string | null | undefined): string {
  if (!value) return '';
  return LOST_REASONS.find((r) => r.value === value)?.label ?? value;
}

/** Same rules as the API: a reason is required, a remark only for "Other", 500 characters at most. */
export function lostReasonError(reason: string, remark: string): string | null {
  if (!reason) return 'Choose a reason';
  if (remark.trim().length > LOST_REMARK_MAX) return `Remark can be at most ${LOST_REMARK_MAX} characters`;
  if (reason === 'other' && !remark.trim()) return 'Add a remark when the reason is Other';
  return null;
}
