import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import type {
  AnalyticsOverviewEnvelope,
  AnalyticsPeriod,
  PatientRevenueSort,
  TherapistPerformanceEnvelope,
} from '../../types/api';

/** Inclusive India-calendar days (YYYY-MM-DD) for a custom range (D-026). */
export interface CustomRange {
  start: string;
  end: string;
}

export const analyticsKeys = {
  all: ['analytics'] as const,
  overview: (
    period: AnalyticsPeriod = 'month',
    sort: PatientRevenueSort = 'collected_amount',
    limit = 5,
    range: CustomRange | null = null,
  ) => [...analyticsKeys.all, 'overview', { period, sort, limit, range }] as const,
  myPerformance: (period: AnalyticsPeriod = 'month', range: CustomRange | null = null) =>
    [...analyticsKeys.all, 'my-performance', { period, range }] as const,
};

/** A custom range replaces the period on the server; both dates are sent together. */
const periodParams = (period: AnalyticsPeriod, range: CustomRange | null) =>
  period === 'custom' && range ? { period, start_date: range.start, end_date: range.end } : { period };

export const fetchAnalyticsOverview = async (
  period: AnalyticsPeriod = 'month',
  patientRevenueSort: PatientRevenueSort = 'collected_amount',
  patientRevenueLimit = 5,
  range: CustomRange | null = null,
): Promise<AnalyticsOverviewEnvelope> => {
  const { data } = await apiClient.get<AnalyticsOverviewEnvelope>('/analytics/overview', {
    params: {
      ...periodParams(period, range),
      patient_revenue_sort: patientRevenueSort,
      patient_revenue_limit: patientRevenueLimit,
    },
  });
  return data;
};

export interface AnalyticsQueryOptions {
  period?: AnalyticsPeriod;
  range?: CustomRange | null;
  enabled?: boolean;
  patientRevenueSort?: PatientRevenueSort;
  patientRevenueLimit?: number;
}

export const useAnalyticsOverview = ({
  period = 'month',
  range = null,
  enabled = true,
  patientRevenueSort = 'collected_amount',
  patientRevenueLimit = 5,
}: AnalyticsQueryOptions = {}) => {
  return useQuery({
    queryKey: analyticsKeys.overview(period, patientRevenueSort, patientRevenueLimit, range),
    queryFn: () => fetchAnalyticsOverview(period, patientRevenueSort, patientRevenueLimit, range),
    enabled: enabled && (period !== 'custom' || !!range),
  });
};

export const fetchMyPerformance = async (
  period: AnalyticsPeriod = 'month',
  range: CustomRange | null = null,
): Promise<TherapistPerformanceEnvelope> => {
  const { data } = await apiClient.get<TherapistPerformanceEnvelope>(
    '/analytics/my-performance',
    { params: periodParams(period, range) },
  );
  return data;
};

export const useMyPerformance = (
  period: AnalyticsPeriod = 'month',
  enabled = true,
  range: CustomRange | null = null,
) => {
  return useQuery({
    queryKey: analyticsKeys.myPerformance(period, range),
    queryFn: () => fetchMyPerformance(period, range),
    enabled: enabled && (period !== 'custom' || !!range),
  });
};

/** Client copy of the API rules: both dates, start not after end, at most 24 months. */
export function customRangeError(start: string, end: string): string | null {
  if (!start || !end) return 'Choose both dates';
  if (start > end) return 'Start date must be on or before the end date';
  const [y, m, d] = start.split('-').map(Number);
  const limitMonth = new Date(Date.UTC(y, m - 1 + 24, 1));
  const lastDay = new Date(Date.UTC(limitMonth.getUTCFullYear(), limitMonth.getUTCMonth() + 1, 0)).getUTCDate();
  const limit = new Date(Date.UTC(limitMonth.getUTCFullYear(), limitMonth.getUTCMonth(), Math.min(d, lastDay)));
  if (new Date(`${end}T00:00:00Z`) > limit) return 'Choose a range of 24 months or less';
  return null;
}
