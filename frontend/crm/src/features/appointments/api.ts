import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { Appointment } from '../../types/api';
import { AppointmentFormValues } from '../../lib/schemas';
import type { AppointmentListQuery } from './listing';

export const APPOINTMENTS_QUERY_KEY = ['appointments'];

/**
 * One page of appointments, filtered, ordered and counted by the server
 * (India days, D-028). `meta.total` is the server count for the whole filter.
 */
export function useAppointmentList(query: AppointmentListQuery, enabled = true) {
  return useQuery({
    queryKey: [...APPOINTMENTS_QUERY_KEY, query],
    queryFn: async () => {
      const res = await apiClient.get('/appointments', { params: query });
      const data: Appointment[] = res.data?.items || res.data?.data || [];
      return { data, meta: { total: Number(res.data?.total ?? data.length) } };
    },
    enabled,
  });
}

export function useCreateAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (values: AppointmentFormValues) => {
      const res = await apiClient.post('/appointments', values);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_QUERY_KEY });
    },
  });
}

export function useUpdateAppointmentStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: Appointment['status'] }) => {
      const res = await apiClient.patch(`/appointments/${id}`, { status });
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_QUERY_KEY });
    },
  });
}

export function useUpdateAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<AppointmentFormValues> }) => {
      const res = await apiClient.patch(`/appointments/${id}`, data);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: APPOINTMENTS_QUERY_KEY });
    },
  });
}

export interface AssignableTherapist {
  id: string;
  name: string;
  role: string;
}

/**
 * Active therapists and admins the user may book with (D-029). It used to
 * read GET /users, which needs `users.view`, so front desk and therapists
 * saw an empty list. With own scope the server returns only the user.
 */
export function useAssignableTherapists(enabled = true) {
  return useQuery<AssignableTherapist[]>({
    queryKey: [...APPOINTMENTS_QUERY_KEY, 'therapists'],
    queryFn: async () => {
      const res = await apiClient.get('/appointments/therapists');
      return Array.isArray(res.data) ? res.data : res.data?.data ?? [];
    },
    enabled,
    staleTime: 60_000,
  });
}
