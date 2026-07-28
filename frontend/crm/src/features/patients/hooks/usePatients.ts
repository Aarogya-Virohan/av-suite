import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patientApi } from '../services/patient.api';

import { PatientIntakeInput } from '../schemas/patient.schema';
import { toast } from 'sonner';

export const usePatients = (page = 1) => {
  return useQuery({
    queryKey: ['patients', page],
    queryFn: async () => {
      const startTime = Date.now();
      const data = await patientApi.fetch(page);
      const latency = Date.now() - startTime;
      localStorage.setItem('api_last_latency', `${latency}ms`);
      return data;
    }
  });
};

export const usePatient = (id: string | null) => {
  return useQuery({
    queryKey: ['patient', id],
    queryFn: async () => {
      if (!id) return null;
      const startTime = Date.now();
      const data = await patientApi.fetchOne(id);
      const latency = Date.now() - startTime;
      localStorage.setItem('api_last_latency', `${latency}ms`);
      return data;
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
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to create patient.');
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
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to update patient.');
    }
  });
};

export const useDeletePatient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await patientApi.delete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Patient moved to Recycle Bin.');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to delete patient.');
    }
  });
};
