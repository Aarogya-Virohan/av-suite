import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { Patient } from '../../types/api';
import { PatientFormValues } from '../../lib/schemas';

export const PATIENTS_QUERY_KEY = ['patients'];

export function usePatients() {
  return useQuery<Patient[]>({
    queryKey: PATIENTS_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get('/patients');
      return res.data?.data || res.data || [];
    },
  });
}

export function usePatient(id: string) {
  return useQuery<Patient | null>({
    queryKey: [...PATIENTS_QUERY_KEY, id],
    queryFn: async () => {
      const res = await apiClient.get(`/patients/${id}`);
      return res.data?.data || res.data || null;
    },
    enabled: !!id,
  });
}

export function useCreatePatient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (values: PatientFormValues) => {
      const res = await apiClient.post('/patients', values);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
    },
  });
}

export function useUpdatePatient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, values }: { id: string; values: Partial<PatientFormValues> }) => {
      const res = await apiClient.patch(`/patients/${id}`, values);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
    },
  });
}

export function useDeletePatient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.delete(`/patients/${id}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
    },
  });
}
