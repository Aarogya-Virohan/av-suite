import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { AnalyticsOverview } from '../../types/api';

export const analyticsKeys = {
  all: ['analytics'] as const,
  overview: () => [...analyticsKeys.all, 'overview'] as const,
  myPerformance: () => [...analyticsKeys.all, 'my-performance'] as const,
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

// Therapist-scoped analytics — RBAC Spec §4: Analytics for Therapist = "Own only"
// Per Rev3 scope: separate endpoint from clinic-wide overview
export interface TherapistPerformance {
  today_appointments: number;
  completed_appointments_this_month: number;
  cancelled_appointments_this_month: number;
  treatment_sessions_this_month: number;
  soap_notes_this_month: number;
  patients_seen_this_month: number;
}

export const fetchMyPerformance = async (): Promise<TherapistPerformance> => {
  const { data } = await apiClient.get('/analytics/my-performance');
  return data.data;
};

export const useMyPerformance = () => {
  return useQuery({
    queryKey: analyticsKeys.myPerformance(),
    queryFn: fetchMyPerformance,
  });
};
