import { z } from 'zod';

/** Every console mutation carries a typed reason (section 6.3 / 11). */
export const REASON_MAX = 1000;

export const reasonField = z
  .string()
  .trim()
  .min(1, 'A reason is required. It is saved in the audit log.')
  .max(REASON_MAX, `Keep the reason under ${REASON_MAX} characters.`);
