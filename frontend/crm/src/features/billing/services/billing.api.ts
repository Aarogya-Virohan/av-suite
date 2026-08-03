import { api } from '@/lib/axios';
import { Invoice, Payment, PatientPackage } from '@/types/crm';
import { InvoiceInput, PaymentInput } from '../schemas/invoice.schema';

export const billingApi = {
  fetchInvoices: async (): Promise<Invoice[]> => {
    const response = await api.get('/invoices');
    return response.data.items || response.data.data || response.data;
  },

  createInvoice: async (data: InvoiceInput): Promise<Invoice> => {
    const response = await api.post('/invoices', data);
    return response.data.items || response.data.data || response.data;
  },

  recordPayment: async (invoiceId: string, data: PaymentInput): Promise<Payment> => {
    const response = await api.post(`/invoices/${invoiceId}/payments`, data);
    return response.data.items || response.data.data || response.data;
  },

  fetchPackages: async (): Promise<PatientPackage[]> => {
    const response = await api.get('/packages');
    return response.data.items || response.data.data || response.data;
  },

  sellPackage: async (patientId: string, data: any): Promise<PatientPackage> => {
    const response = await api.post(`/patients/${patientId}/packages`, data);
    return response.data.items || response.data.data || response.data;
  }
};
export default billingApi;
