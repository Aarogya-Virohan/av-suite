import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '../services/settings.api';
import { useCRMStore } from '@/lib/store';
import { ClinicBranding } from '@/types/crm';
import { toast } from 'sonner';

export const useBranding = (slug = 'default') => {
  const store = useCRMStore();
  return useQuery({
    queryKey: ['branding', slug],
    queryFn: async () => {
      try {
        return await settingsApi.fetchBranding(slug);
      } catch (err) {
        return store.branding;
      }
    }
  });
};

export const useSaveBranding = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (data: ClinicBranding) => {
      try {
        await settingsApi.saveBranding(data);
      } catch (err) {
        store.updateBranding(data);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['branding'] });
      toast.success('Clinic branding saved successfully.');
    }
  });
};
