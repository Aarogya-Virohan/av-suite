import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';

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
