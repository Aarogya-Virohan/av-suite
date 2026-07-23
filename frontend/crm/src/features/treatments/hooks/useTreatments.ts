import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { treatmentApi } from '../services/treatment.api';
import { useCRMStore } from '@/lib/store';
import { TreatmentSession, SOAPAssessment } from '@/types/crm';
import { toast } from 'sonner';

export const useTreatments = (patientId: string) => {
  const store = useCRMStore();
  return useQuery({
    queryKey: ['treatments', patientId],
    queryFn: async () => {
      try {
        return await treatmentApi.fetch(patientId);
      } catch (err) {
        return store.treatments.filter(t => t.patientId === patientId);
      }
    },
    enabled: !!patientId
  });
};

export const useCreateTreatment = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (data: Partial<TreatmentSession>) => {
      try {
        return await treatmentApi.create(data);
      } catch (err) {
        store.addTreatment({
          patientId: data.patientId!,
          date: data.date!,
          therapist: data.therapist,
          painScore: data.painScore,
          treatment: data.treatment!,
          homeAdvice: data.homeAdvice
        });
        return store.treatments[0];
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['treatments', data.patientId] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Treatment session logged.');
    }
  });
};

export const useCreateAssessment = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (data: Partial<SOAPAssessment>) => {
      try {
        return await treatmentApi.createAssessment(data);
      } catch (err) {
        store.addAssessment({
          patientId: data.patientId!,
          specialty: data.specialty!,
          isReassessment: data.isReassessment || false,
          formData: data.formData || {}
        });
        return store.assessments[0];
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['assessments', data.patientId] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('SOAP clinical assessment saved.');
    }
  });
};
