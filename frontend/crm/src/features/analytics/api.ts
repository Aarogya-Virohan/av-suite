import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import type {
  AnalyticsOverviewEnvelope,
  AnalyticsPeriod,
  PatientRevenueSort,
  TherapistPerformanceEnvelope,
} from '../../types/api';

export const analyticsKeys = {
  all: ['analytics'] as const,
  overview: (
    period: AnalyticsPeriod = 'month',
    sort: PatientRevenueSort = 'collected_amount',
    limit = 5,
  ) => [...analyticsKeys.all, 'overview', { period, sort, limit }] as const,
  myPerformance: (period: AnalyticsPeriod = 'month') =>
    [...analyticsKeys.all, 'my-performance', { period }] as const,
};

export const fetchAnalyticsOverview = async (
  period: AnalyticsPeriod = 'month',
  patientRevenueSort: PatientRevenueSort = 'collected_amount',
  patientRevenueLimit = 5,
): Promise<AnalyticsOverviewEnvelope> => {
  const { data } = await apiClient.get<AnalyticsOverviewEnvelope>('/analytics/overview', {
    params: {
      period,
      patient_revenue_sort: patientRevenueSort,
      patient_revenue_limit: patientRevenueLimit,
    },
  });
  return data;
};

export interface AnalyticsQueryOptions {
  period?: AnalyticsPeriod;
  enabled?: boolean;
  patientRevenueSort?: PatientRevenueSort;
  patientRevenueLimit?: number;
}

export const useAnalyticsOverview = ({
  period = 'month',
  enabled = true,
  patientRevenueSort = 'collected_amount',
  patientRevenueLimit = 5,
}: AnalyticsQueryOptions = {}) => {
  return useQuery({
    queryKey: analyticsKeys.overview(period, patientRevenueSort, patientRevenueLimit),
    queryFn: () => fetchAnalyticsOverview(period, patientRevenueSort, patientRevenueLimit),
    enabled,
  });
};

export const fetchMyPerformance = async (
  period: AnalyticsPeriod = 'month',
): Promise<TherapistPerformanceEnvelope> => {
  const { data } = await apiClient.get<TherapistPerformanceEnvelope>(
    '/analytics/my-performance',
    { params: { period } },
  );
  return data;
};

export const useMyPerformance = (
  period: AnalyticsPeriod = 'month',
  enabled = true,
) => {
  return useQuery({
    queryKey: analyticsKeys.myPerformance(period),
    queryFn: () => fetchMyPerformance(period),
    enabled,
  });
};
