import { api } from '@/lib/axios';
import { Appointment, AppointmentRequest } from '@/types/crm';
import { AppointmentInput } from '../schemas/appointment.schema';

export const appointmentApi = {
  fetch: async (): Promise<Appointment[]> => {
    const response = await api.get('/appointments');
    const data = response.data.data || response.data;
    
    if (data && Array.isArray(data.items)) {
      const items = data.items as Appointment[] & { total?: number; offset?: number; limit?: number };
      items.total = data.total;
      items.offset = data.offset;
      items.limit = data.limit;
      return items;
    }
    
    return data;
  },

  create: async (data: AppointmentInput): Promise<Appointment> => {
    const payload = {
      patient_id: data.patient_id,
      therapist_id: data.therapist_id,
      scheduled_at: new Date(`${data.date}T${data.time}`).toISOString(),
      duration_minutes: data.duration_minutes
    };
    const response = await api.post('/appointments', payload);
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
