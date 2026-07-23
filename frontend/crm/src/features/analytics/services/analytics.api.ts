import { api } from '@/lib/axios';

export const analyticsApi = {
  fetchOverview: async (): Promise<any> => {
    const response = await api.get('/analytics/overview');
    return response.data.data || response.data;
  }
};
export default analyticsApi;
