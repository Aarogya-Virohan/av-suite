import { api } from '@/lib/axios';
import { TreatmentSession, SOAPAssessment } from '@/types/crm';

export const treatmentApi = {
  fetch: async (patientId: string): Promise<TreatmentSession[]> => {
    const response = await api.get(`/treatments?patient_id=${patientId}`);
    return response.data.data || response.data;
  },

  create: async (data: Partial<TreatmentSession>): Promise<TreatmentSession> => {
    const response = await api.post('/treatments', data);
    return response.data.data || response.data;
  },

  createAssessment: async (data: Partial<SOAPAssessment>): Promise<SOAPAssessment> => {
    const response = await api.post('/assessments', data);
    return response.data.data || response.data;
  }
};
export default treatmentApi;
