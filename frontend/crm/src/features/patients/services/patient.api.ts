import { api } from '@/lib/axios';
import { Patient } from '@/types/crm';
import { PatientIntakeInput } from '../schemas/patient.schema';

export const patientApi = {
  fetch: async (page = 1): Promise<Patient[]> => {
    const response = await api.get(`/patients?page=${page}`);
    return response.data.data || response.data;
  },

  fetchOne: async (id: string): Promise<Patient> => {
    const response = await api.get(`/patients/${id}`);
    return response.data.data || response.data;
  },

  create: async (data: PatientIntakeInput): Promise<Patient> => {
    const nameParts = (data.full_name || '').trim().split(/\s+/);
    const firstName = nameParts[0] || '';
    const lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : nameParts[0] || '';

    const payload = {
      first_name: firstName,
      last_name: lastName,
      phone: data.phone || undefined
    };
    const response = await api.post('/patients', payload);
    return response.data.data || response.data;
  },

  update: async (id: string, data: Partial<PatientIntakeInput>): Promise<Patient> => {
    // TODO: Enable when backend implements PATCH/DELETE patients endpoints.
    throw new Error('Not implemented: Update patient');
  },

  delete: async (id: string): Promise<void> => {
    // TODO: Enable when backend implements PATCH/DELETE patients endpoints.
    throw new Error('Not implemented: Delete patient');
  }
};
export default patientApi;
