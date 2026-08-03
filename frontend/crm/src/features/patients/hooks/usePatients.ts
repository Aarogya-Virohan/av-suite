import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patientApi } from '../services/patient.api';
import { PatientIntakeInput } from '../schemas/patient.schema';
import { toast } from 'sonner';

export const usePatients = (page = 1) => {
  return useQuery({
    queryKey: ['patients', page],
    queryFn: () => patientApi.fetch(page),
  });
};

export const usePatient = (id: string | null) => {
  return useQuery({
    queryKey: ['patient', id],
    queryFn: () => patientApi.fetchOne(id!),
    enabled: !!id,
  });
};

export const useCreatePatient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PatientIntakeInput) => patientApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Patient record created successfully!');
    },
  });
};

export const useUpdatePatient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<PatientIntakeInput> }) =>
      patientApi.update(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      if (data?.id) {
        queryClient.invalidateQueries({ queryKey: ['patient', data.id] });
      }
      toast.success('Patient record updated.');
    },
  });
};

export const useDeletePatient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => patientApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Patient moved to Recycle Bin.');
    },
  });
};
