import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leadApi } from '../services/lead.api';
import { useCRMStore } from '@/lib/store';
import { LeadInput } from '../schemas/lead.schema';
import { toast } from 'sonner';

export const useLeads = () => {
  const store = useCRMStore();
  return useQuery({
    queryKey: ['leads'],
    queryFn: async () => {
      const startTime = Date.now();
      try {
        const data = await leadApi.fetch();
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms`);
        return data;
      } catch (err) {
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms (Mock)`);
        return store.leads;
      }
    }
  });
};

export const useCreateLead = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (data: LeadInput) => {
      try {
        return await leadApi.create(data);
      } catch (err) {
        store.addLead({
          name: data.name,
          mobile: data.mobile || undefined,
          source: data.source,
          stage: data.stage,
          notes: data.notes
        });
        return store.leads[0];
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead prospect created successfully!');
    }
  });
};

export const useUpdateLead = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<LeadInput> }) => {
      try {
        return await leadApi.update(id, data);
      } catch (err) {
        store.updateLead(id, data as any);
        return store.leads.find(l => l.id === id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    }
  });
};

export const useConvertLead = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (id: string) => {
      try {
        return await leadApi.convert(id);
      } catch (err) {
        return store.convertLeadToPatient(id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Lead converted to Patient profile.');
    }
  });
};
