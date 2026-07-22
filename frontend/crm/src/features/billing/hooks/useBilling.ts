import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { billingApi } from '../services/billing.api';
import { useCRMStore } from '@/lib/store';
import { InvoiceInput, PaymentInput } from '../schemas/invoice.schema';
import { toast } from 'sonner';
import { calculateInvoiceTotals } from '../utils/invoiceMath';

export const useInvoices = () => {
  const store = useCRMStore();
  return useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      const startTime = Date.now();
      try {
        const data = await billingApi.fetchInvoices();
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms`);
        return data;
      } catch (err) {
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms (Mock)`);
        return store.invoices;
      }
    }
  });
};

export const useCreateInvoice = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (data: InvoiceInput) => {
      try {
        return await billingApi.createInvoice(data);
      } catch (err) {
        const pt = store.patients.find(p => p.id === data.patient_id);
        const totals = calculateInvoiceTotals({
          baseAmount: data.amount,
          discountAmount: data.discount,
          gstPercent: data.gst_percent
        });
        
        store.addInvoice({
          patientId: data.patient_id,
          patientName: pt ? pt.name : 'Unknown Patient',
          description: data.description,
          amount: totals.subtotal,
          tax: totals.tax,
          discount: totals.discount,
          total: totals.grandTotal,
          date: new Date().toISOString().slice(0, 10)
        });
        return store.invoices[0];
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Invoice created successfully!');
    }
  });
};

export const useRecordPayment = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async ({ invoiceId, data }: { invoiceId: string; data: PaymentInput }) => {
      try {
        return await billingApi.recordPayment(invoiceId, data);
      } catch (err) {
        store.recordPayment({
          invoiceId,
          patientId: store.invoices.find(i => i.id === invoiceId)?.patientId || '',
          amount: data.amount,
          mode: data.mode,
          reference: data.reference,
          date: new Date().toISOString().slice(0, 10)
        });
        return store.payments[0];
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Payment recorded successfully.');
    }
  });
};

export const usePackages = () => {
  const store = useCRMStore();
  return useQuery({
    queryKey: ['packages'],
    queryFn: async () => {
      try {
        return await billingApi.fetchPackages();
      } catch (err) {
        return store.packages;
      }
    }
  });
};

export const useCreatePackage = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async ({ patientId, data }: { patientId: string; data: any }) => {
      try {
        return await billingApi.sellPackage(patientId, data);
      } catch (err) {
        const pt = store.patients.find(p => p.id === patientId);
        store.addPackage({
          patientId,
          patientName: pt ? pt.name : 'Unknown Patient',
          packageName: data.packageName,
          totalSessions: data.totalSessions,
          sessionsUsed: 0,
          amount: data.amount,
          startDate: new Date().toISOString().slice(0, 10),
          status: 'Active'
        });
        return store.packages[0];
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packages'] });
      toast.success('Package purchased successfully!');
    }
  });
};
