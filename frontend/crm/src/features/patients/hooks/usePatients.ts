import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patientApi } from '../services/patient.api';
import { PatientIntakeInput } from '../schemas/patient.schema';
import { toast } from 'sonner';

export const usePatients = (page = 1) => {
  return useQuery({
    queryKey: ['patients', page],
    queryFn: async () => {
      return await patientApi.fetch(page);
    }
  });
};

export const usePatient = (id: string | null) => {
  return useQuery({
    queryKey: ['patient', id],
    queryFn: async () => {
      if (!id) return null;
      return await patientApi.fetchOne(id);
    },
    enabled: !!id
  });
};

export const useCreatePatient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PatientIntakeInput) => {
      return await patientApi.create(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Patient record created successfully!');
    }
  });
};

export const useUpdatePatient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<PatientIntakeInput> }) => {
      return await patientApi.update(id, data);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      if (data?.id) {
        queryClient.invalidateQueries({ queryKey: ['patient', data.id] });
      }
      toast.success('Patient record updated.');
    }
  });
};

export const useDeletePatient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return await patientApi.delete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Patient moved to Recycle Bin.');
    }
  });
};
