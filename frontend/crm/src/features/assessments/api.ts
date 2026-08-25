import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';

export const ASSESSMENTS_QUERY_KEY = ['assessments'];

export function useAssessments(patientId: string) {
  return useQuery({
    queryKey: [...ASSESSMENTS_QUERY_KEY, { patientId }],
    queryFn: async () => {
      const res = await apiClient.get('/assessments', {
        params: { patient_id: patientId },
      });
      return res.data as { data: any[]; meta: any };
    },
    enabled: !!patientId,
  });
}

import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useCreateAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (values: any) => {
      const res = await apiClient.post('/assessments', values);
      return res.data?.data || res.data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ASSESSMENTS_QUERY_KEY });
    },
  });
}

export function useUpdateAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, values }: { id: string; values: any }) => {
      const res = await apiClient.patch(`/assessments/${id}`, values);
      return res.data?.data || res.data;
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ASSESSMENTS_QUERY_KEY });
    },
  });
}
