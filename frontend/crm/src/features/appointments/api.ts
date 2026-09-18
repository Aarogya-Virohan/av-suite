import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { Appointment } from '../../types/api';
import { AppointmentFormValues } from '../../lib/schemas';

export const APPOINTMENTS_QUERY_KEY = ['appointments'];

export function useAppointments(startDate?: string, endDate?: string, page = 1, page_size = 10) {
  return useQuery({
    queryKey: [...APPOINTMENTS_QUERY_KEY, { startDate, endDate, page, page_size }],
    queryFn: async () => {
      const res = await apiClient.get('/appointments', {
        params: { 
          start_date: startDate || undefined, 
          end_date: endDate || undefined,
          offset: (page - 1) * page_size,
          limit: page_size 
        },
      });
      // Backend returns { items: Appointment[], total: number, offset: number, limit: number }
      const data = res.data?.items || res.data?.data || [];
      return { data, meta: { total: res.data?.total || 0, page, page_size } };
    },
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
