import { api } from '@/lib/axios';
import { Lead } from '@/types/crm';
import { LeadInput } from '../schemas/lead.schema';

export const leadApi = {
  fetch: async (): Promise<Lead[]> => {
    const response = await api.get('/leads');
    return response.data.items || response.data.data || response.data;
  },

  create: async (data: LeadInput): Promise<Lead> => {
    const response = await api.post('/leads', data);
    return response.data.items || response.data.data || response.data;
  },

  update: async (id: string, data: Partial<LeadInput>): Promise<Lead> => {
    const response = await api.patch(`/leads/${id}`, data);
    return response.data.items || response.data.data || response.data;
  },

  convert: async (id: string): Promise<any> => {
    const response = await api.post(`/leads/${id}/convert`);
    return response.data.items || response.data.data || response.data;
  }
};
export default leadApi;
