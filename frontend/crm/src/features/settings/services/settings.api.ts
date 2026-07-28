import { api } from '@/lib/axios';
import { ClinicBranding } from '@/types/crm';

export const settingsApi = {
  fetchBranding: async (slug: string): Promise<ClinicBranding> => {
    const response = await api.get(`/booking/branding/${slug}`);
    return response.data.data || response.data;
  },

  saveBranding: async (data: ClinicBranding): Promise<void> => {
    await api.patch('/api/v1/settings/clinic', data);
  }
};
export default settingsApi;
