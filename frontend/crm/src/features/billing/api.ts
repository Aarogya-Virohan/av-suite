import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { Invoice, Payment, Package } from '../../types/api';
import { InvoiceFormValues, PaymentFormValues } from '../../lib/schemas';

export const BILLING_QUERY_KEY = ['billing'];

export function useInvoices(enabled = true) {
  return useQuery<Invoice[]>({
    queryKey: [...BILLING_QUERY_KEY, 'invoices'],
    queryFn: async () => {
      const res = await apiClient.get('/invoices');
      const raw = res.data?.items ?? res.data?.data ?? res.data;
      if (Array.isArray(raw)) return raw;
      if (raw && Array.isArray(raw.items)) return raw.items;
      return [];
    },
    enabled,
  });
}

export function usePayments(enabled = true) {
  return useQuery<Payment[]>({
    queryKey: [...BILLING_QUERY_KEY, 'payments'],
    queryFn: async () => {
      const res = await apiClient.get('/payments');
      const raw = res.data?.items ?? res.data?.data ?? res.data;
      if (Array.isArray(raw)) return raw;
      if (raw && Array.isArray(raw.items)) return raw.items;
      return [];
    },
    enabled,
  });
}

/** Payments recorded against one invoice (for the receipt). */
export function useInvoicePayments(invoiceId: string | null | undefined, enabled = true) {
  return useQuery<Payment[]>({
    queryKey: [...BILLING_QUERY_KEY, 'payments', 'invoice', invoiceId],
    queryFn: async () => {
      const res = await apiClient.get('/payments', { params: { invoice_id: invoiceId, limit: 500 } });
      const raw = res.data?.items ?? res.data?.data ?? res.data;
      if (Array.isArray(raw)) return raw;
      if (raw && Array.isArray(raw.items)) return raw.items;
      return [];
    },
    enabled: enabled && !!invoiceId,
  });
}

export function usePackages(enabled = true) {
  return useQuery<Package[]>({
    queryKey: [...BILLING_QUERY_KEY, 'packages'],
    queryFn: async () => {
      const res = await apiClient.get('/packages');
      const raw = res.data?.items ?? res.data?.data ?? res.data;
      if (Array.isArray(raw)) return raw;
      if (raw && Array.isArray(raw.items)) return raw.items;
      return [];
    },
    enabled,
  });
}

/** Form values plus the optional percent fields (D-026); an amount is left out when its percent is sent. */
export type InvoiceCreatePayload = Omit<InvoiceFormValues, 'discount_amount' | 'tax_amount'> & {
  discount_amount?: number;
  tax_amount?: number;
  discount_percent?: string;
  tax_percent?: string;
};

export function useCreateInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (values: InvoiceCreatePayload) => {
      const res = await apiClient.post('/invoices', values);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BILLING_QUERY_KEY });
    },
  });
}

export function useRecordPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (values: PaymentFormValues) => {
      const res = await apiClient.post(`/invoices/${values.invoice_id}/payments`, values);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BILLING_QUERY_KEY });
    },
  });
}

export type InvoicePdfKind = 'invoice' | 'receipt';

/** Same name the server sends: Invoice-INV-0001.pdf / Receipt-INV-0001.pdf (L-41). */
export function invoicePdfFilename(kind: InvoicePdfKind, invoiceNumber: string): string {
  const safe = invoiceNumber.replace(/[^A-Za-z0-9_-]/g, '-').replace(/^-+|-+$/g, '') || 'invoice';
  return `${kind === 'receipt' ? 'Receipt' : 'Invoice'}-${safe}.pdf`;
}

/**
 * Fetch the server-rendered PDF (GET /invoices/{id}/pdf/download) and save it.
 * The name is built here because CORS does not expose Content-Disposition.
 */
export async function downloadInvoicePdf(invoiceId: string, invoiceNumber: string, kind: InvoicePdfKind) {
  const res = await apiClient.get(`/invoices/${invoiceId}/pdf/download`, {
    params: kind === 'receipt' ? { kind } : undefined,
    responseType: 'blob',
  });
  const blob = res.data instanceof Blob ? res.data : new Blob([res.data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = invoicePdfFilename(kind, invoiceNumber);
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}
