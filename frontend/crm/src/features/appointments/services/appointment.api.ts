import { api } from '@/lib/axios';
import { Appointment, AppointmentRequest } from '@/types/crm';
import { AppointmentInput } from '../schemas/appointment.schema';

export const appointmentApi = {
  fetch: async (): Promise<Appointment[]> => {
    const response = await api.get('/appointments');
    return response.data.data || response.data;
  },

  create: async (data: AppointmentInput): Promise<Appointment> => {
    const response = await api.post('/appointments', data);
    return response.data.data || response.data;
  },

  updateStatus: async (id: string, status: string): Promise<Appointment> => {
    const response = await api.patch(`/appointments/${id}`, { status });
    return response.data.data || response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/appointments/${id}`);
  },

  fetchRequests: async (): Promise<AppointmentRequest[]> => {
    const response = await api.get('/appointment-requests');
    return response.data.data || response.data;
  },

  approveRequest: async (id: string, therapistId?: string, duration?: number): Promise<void> => {
    await api.post(`/appointment-requests/${id}/approve`, {
      therapist_id: therapistId,
      duration_minutes: duration
    });
  },

  rejectRequest: async (id: string): Promise<void> => {
    await api.post(`/appointment-requests/${id}/reject`);
  }
};
export default appointmentApi;
