import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';

export function usePrescriptions(patientId: string) {
  return useQuery({
    queryKey: ['prescriptions', patientId],
    queryFn: async () => {
      const res = await apiClient.get('/prescriptions', { params: { patient_id: patientId } });
      return res.data?.data || res.data;
    },
    enabled: !!patientId,
    // A 403 (Rx not enabled for this clinic, or no permission) will not
    // change on retry.
    retry: (count, error: any) => error?.response?.status !== 403 && count < 1,
  });
}

export function useCreatePrescription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (values: any) => {
      const res = await apiClient.post('/prescriptions', values);
      return res.data?.data || res.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['prescriptions'] }),
  });
}

export function useGeneratePrescriptionPdf() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.post(`/prescriptions/${id}/pdf`);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prescriptions'] });
    },
  });
}
