import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { treatmentApi } from '../services/treatment.api';
import { TreatmentSession, SOAPAssessment } from '@/types/crm';
import { toast } from 'sonner';

export const useTreatments = (patientId: string) => {
  return useQuery({
    queryKey: ['treatments', patientId],
    queryFn: async () => {
      return await treatmentApi.fetch(patientId);
    },
    enabled: !!patientId
  });
};

export const useCreateTreatment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<TreatmentSession>) => {
      return await treatmentApi.create(data);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['treatments', data?.patientId] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Treatment session logged.');
    }
  });
};

export const useCreateAssessment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<SOAPAssessment>) => {
      return await treatmentApi.createAssessment(data);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['assessments', data?.patientId] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('SOAP clinical assessment saved.');
    }
  });
};
