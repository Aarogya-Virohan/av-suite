import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { TreatmentSessionFormValues } from '../../lib/schemas';

export const TREATMENTS_QUERY_KEY = ['treatments'];

export function useTreatments(patientId: string) {
  return useQuery({
    queryKey: [...TREATMENTS_QUERY_KEY, { patientId }],
    queryFn: async () => {
      const res = await apiClient.get('/treatments', {
        params: { patient_id: patientId },
      });
      return res.data as { data: any[]; meta: any };
    },
    enabled: !!patientId,
  });
}

export function useCreateTreatmentSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (values: TreatmentSessionFormValues) => {
      const res = await apiClient.post('/treatments', values);
      return res.data?.data || res.data;
    },
    onSuccess: (_data, variables) => {
      // Invalidate the treatments list for this specific patient
      queryClient.invalidateQueries({
        queryKey: [...TREATMENTS_QUERY_KEY, { patientId: variables.patient_id }],
      });
    },
  });
}
