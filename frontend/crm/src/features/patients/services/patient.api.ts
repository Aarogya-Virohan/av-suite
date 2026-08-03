import { api } from '@/lib/axios';
import { Patient } from '@/types/crm';
import { PatientIntakeInput } from '../schemas/patient.schema';

export const patientApi = {
  fetch: async (page = 1): Promise<Patient[]> => {
    const response = await api.get(`/patients?page=${page}`);
    return response.data.items || response.data.data || response.data;
  },

  fetchOne: async (id: string): Promise<Patient> => {
    const response = await api.get(`/patients/${id}`);
    return response.data.items || response.data.data || response.data;
  },

  create: async (data: PatientIntakeInput): Promise<Patient> => {
    // Translate fields to snake_case if required by fastapi backend
    const payload = {
      full_name: data.full_name,
      phone: data.phone,
      age: data.age,
      gender: data.gender,
      chief_complaint: data.chief_complaint,
      referral_source: data.referral_source
    };
    const response = await api.post('/patients', payload);
    return response.data.items || response.data.data || response.data;
  },

  update: async (id: string, data: Partial<PatientIntakeInput>): Promise<Patient> => {
    const response = await api.patch(`/patients/${id}`, data);
    return response.data.items || response.data.data || response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/patients/${id}`);
  }
};
export default patientApi;
