import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { billingApi } from '../services/billing.api';

import { InvoiceInput, PaymentInput } from '../schemas/invoice.schema';
import { toast } from 'sonner';
import { calculateInvoiceTotals } from '../utils/invoiceMath';

export const useInvoices = () => {
  return useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      const startTime = Date.now();
      const data = await billingApi.fetchInvoices();
      const latency = Date.now() - startTime;
      localStorage.setItem('api_last_latency', `${latency}ms`);
      return data;
    }
  });
};

export const useCreateInvoice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: InvoiceInput) => {
      return await billingApi.createInvoice(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Invoice created successfully!');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to create invoice.');
    }
  });
};

export const useRecordPayment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ invoiceId, data }: { invoiceId: string; data: PaymentInput }) => {
      return await billingApi.recordPayment(invoiceId, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Payment recorded successfully.');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to record payment.');
    }
  });
};

export const usePackages = () => {
  return useQuery({
    queryKey: ['packages'],
    queryFn: async () => {
      return await billingApi.fetchPackages();
    }
  });
};

export const useCreatePackage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ patientId, data }: { patientId: string; data: any }) => {
      return await billingApi.sellPackage(patientId, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packages'] });
      toast.success('Package purchased successfully!');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to create package.');
    }
  });
};
