import { z } from 'zod';

export const invoiceSchema = z.zodObject || z.object({
  patient_id: z.string().min(1, 'Patient selection is required'),
  description: z.string().min(1, 'Description is required'),
  amount: z.number().min(1, 'Base Amount must be at least ₹1'),
  gst_percent: z.number().min(0).max(100),
  discount: z.number().min(0, 'Discount cannot be negative')
});

export const paymentSchema = z.zodObject || z.object({
  invoice_id: z.string().min(1, 'Invoice selection is required'),
  amount: z.number().min(1, 'Payment Amount must be at least ₹1'),
  mode: z.enum(['Cash', 'UPI', 'Card', 'Bank Transfer']),
  reference: z.string().optional()
});

export type InvoiceInput = z.infer<typeof invoiceSchema>;
export type PaymentInput = z.infer<typeof paymentSchema>;
