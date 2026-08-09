import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '../services/settings.api';

import { ClinicBranding } from '@/types/crm';
import { toast } from 'sonner';

export const useBranding = (slug = 'default') => {
  return useQuery({
    queryKey: ['branding', slug],
    queryFn: async () => {
      return await settingsApi.fetchBranding(slug);
    }
  });
};

export const useSaveBranding = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ClinicBranding) => {
      await settingsApi.saveBranding(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['branding'] });
      toast.success('Clinic branding saved successfully.');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to save branding.');
    }
  });
};
