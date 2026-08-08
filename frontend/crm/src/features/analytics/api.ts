import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { AnalyticsOverview } from '../../types/api';

export const analyticsKeys = {
  all: ['analytics'] as const,
  overview: () => [...analyticsKeys.all, 'overview'] as const,
};

export const fetchAnalyticsOverview = async (): Promise<AnalyticsOverview> => {
  const { data } = await apiClient.get('/analytics/overview');
  return data.data; // Standardized API response { data: ... }
};

export const useAnalyticsOverview = () => {
  return useQuery({
    queryKey: analyticsKeys.overview(),
    queryFn: fetchAnalyticsOverview,
  });
};
