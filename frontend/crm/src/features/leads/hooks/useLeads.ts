import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leadApi } from '../services/lead.api';

import { LeadInput } from '../schemas/lead.schema';
import { toast } from 'sonner';

export const useLeads = () => {
  return useQuery({
    queryKey: ['leads'],
    queryFn: async () => {
      const startTime = Date.now();
      const data = await leadApi.fetch();
      const latency = Date.now() - startTime;
      localStorage.setItem('api_last_latency', `${latency}ms`);
      return data;
    }
  });
};

export const useCreateLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: LeadInput) => {
      return await leadApi.create(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead prospect created successfully!');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to create lead.');
    }
  });
};

export const useUpdateLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<LeadInput> }) => {
      return await leadApi.update(id, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead updated successfully!');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to update lead.');
    }
  });
};

export const useConvertLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return await leadApi.convert(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Lead converted to Patient profile.');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to convert lead.');
    }
  });
};
