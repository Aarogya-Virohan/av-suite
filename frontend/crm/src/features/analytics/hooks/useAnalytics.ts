import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../services/analytics.api';
import { useCRMStore } from '@/lib/store';

export const useAnalyticsOverview = () => {
  const store = useCRMStore();
  return useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: async () => {
      try {
        return await analyticsApi.fetchOverview();
      } catch (err) {
        // Build derived overview from mock store data
        const activePatients = store.patients.filter(p => p.status === 'Active').length;
        const totalInvoices = store.invoices.length;
        const totalBilled = store.invoices.reduce((sum, i) => sum + i.total, 0);
        const totalCollected = store.invoices.filter(i => i.status === 'Paid').reduce((sum, i) => sum + i.total, 0);
        
        return {
          activePatients,
          totalInvoices,
          totalBilled,
          totalCollected,
          appointmentsCount: store.appointments.length
        };
      }
    }
  });
};
