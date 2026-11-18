/**
 * A discount above this percent of the subtotal needs a written reason.
 * Mirrors DISCOUNT_REASON_THRESHOLD in backend/app/services/billing.py;
 * the server rejects the invoice (422) when the reason is missing.
 */
export const DISCOUNT_REASON_THRESHOLD = 20;

export interface DiscountInput {
  mode: 'amount' | 'percent';
  /** Percent as typed (percent mode). */
  percent: number;
  /** Discount in rupees (amount mode). */
  amount: number;
  /** Invoice subtotal in rupees. */
  subtotal: number;
}

const toPaise = (rupees: number) => Math.round(rupees * 100);

/**
 * Same test as the server, in whole paise / hundredths so that exactly 20%
 * never trips on float error:
 * - percent mode: the percent sent (rounded to 2 places) is above 20;
 * - amount mode: the discount is above 20% of the subtotal.
 */
export function needsDiscountReason({ mode, percent, amount, subtotal }: DiscountInput): boolean {
  if (mode === 'percent') {
    return Math.round(percent * 100) > DISCOUNT_REASON_THRESHOLD * 100;
  }
  return toPaise(amount) * 100 > toPaise(subtotal) * DISCOUNT_REASON_THRESHOLD;
}
