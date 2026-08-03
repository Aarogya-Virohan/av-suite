import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { billingApi } from '../services/billing.api';
import { InvoiceInput, PaymentInput } from '../schemas/invoice.schema';
import { toast } from 'sonner';

export const useInvoices = () => {
  return useQuery({
    queryKey: ['invoices'],
    queryFn: () => billingApi.fetchInvoices(),
  });
};

export const useCreateInvoice = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: InvoiceInput) => billingApi.createInvoice(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Invoice created successfully!');
    },
  });
};

export const useRecordPayment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ invoiceId, data }: { invoiceId: string; data: PaymentInput }) =>
      billingApi.recordPayment(invoiceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      toast.success('Payment recorded successfully.');
    },
  });
};

export const usePackages = () => {
  return useQuery({
    queryKey: ['packages'],
    queryFn: () => billingApi.fetchPackages(),
  });
};

export const useCreatePackage = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ patientId, data }: { patientId: string; data: any }) =>
      billingApi.sellPackage(patientId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packages'] });
      toast.success('Package purchased successfully!');
    },
  });
};
