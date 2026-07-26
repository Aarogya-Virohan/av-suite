import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../services/analytics.api';
export const useAnalyticsOverview = () => {
  return useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: async () => {
      return await analyticsApi.fetchOverview();
    }
  });
};
