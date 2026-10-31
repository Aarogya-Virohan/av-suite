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
