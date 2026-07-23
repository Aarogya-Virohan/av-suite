export interface InvoiceMathInput {
  baseAmount: number;
  discountAmount: number;
  gstPercent: number;
}

export interface InvoiceMathOutput {
  subtotal: number;
  discount: number;
  tax: number;
  grandTotal: number;
}

export const calculateInvoiceTotals = ({
  baseAmount,
  discountAmount,
  gstPercent
}: InvoiceMathInput): InvoiceMathOutput => {
  const subtotal = Math.max(0, baseAmount);
  const discount = Math.max(0, Math.min(subtotal, discountAmount));
  const taxableAmount = Math.max(0, subtotal - discount);
  const tax = Math.round((taxableAmount * gstPercent) / 100);
  const grandTotal = Math.max(0, taxableAmount + tax);

  return {
    subtotal,
    discount,
    tax,
    grandTotal
  };
};
