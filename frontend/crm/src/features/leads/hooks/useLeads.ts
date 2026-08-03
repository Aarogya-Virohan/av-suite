import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leadApi } from '../services/lead.api';
import { LeadInput } from '../schemas/lead.schema';
import { toast } from 'sonner';

export const useLeads = () => {
  return useQuery({
    queryKey: ['leads'],
    queryFn: () => leadApi.fetch(),
  });
};

export const useCreateLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: LeadInput) => leadApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead prospect created successfully!');
    },
  });
};

export const useUpdateLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<LeadInput> }) =>
      leadApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
  });
};

export const useConvertLead = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => leadApi.convert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Lead converted to Patient profile.');
    },
  });
};
