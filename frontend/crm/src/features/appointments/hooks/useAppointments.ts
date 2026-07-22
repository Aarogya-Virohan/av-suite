import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { appointmentApi } from '../services/appointment.api';
import { useCRMStore } from '@/lib/store';
import { AppointmentInput } from '../schemas/appointment.schema';
import { toast } from 'sonner';

export const useAppointments = () => {
  const store = useCRMStore();
  return useQuery({
    queryKey: ['appointments'],
    queryFn: async () => {
      const startTime = Date.now();
      try {
        const data = await appointmentApi.fetch();
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms`);
        return data;
      } catch (err) {
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms (Mock)`);
        return store.appointments;
      }
    }
  });
};

export const useCreateAppointment = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (data: AppointmentInput) => {
      try {
        return await appointmentApi.create(data);
      } catch (err) {
        const pt = store.patients.find(p => p.id === data.patient_id);
        const ther = store.therapists.find(t => t.id === data.therapist_id);
        
        store.addAppointment({
          patientId: data.patient_id,
          patientName: pt ? pt.name : 'Unknown Patient',
          patientMobile: pt?.mobile,
          therapist: ther ? ther.name : 'Unassigned',
          date: data.date,
          time: data.time,
          durationMinutes: data.duration_minutes,
          status: 'Confirmed',
          source: 'manual',
          notes: data.notes
        });
        return store.appointments[0];
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      toast.success('Appointment booked successfully!');
    }
  });
};

export const useUpdateAppointmentStatus = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      try {
        return await appointmentApi.updateStatus(id, status);
      } catch (err) {
        store.updateAppointmentStatus(id, status as any);
        return store.appointments.find(a => a.id === id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      toast.success('Appointment status updated.');
    }
  });
};

export const useDeleteAppointment = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (id: string) => {
      try {
        await appointmentApi.delete(id);
      } catch (err) {
        store.deleteAppointment(id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      toast.success('Appointment moved to Recycle Bin.');
    }
  });
};

export const useAppointmentRequests = () => {
  const store = useCRMStore();
  return useQuery({
    queryKey: ['appointmentRequests'],
    queryFn: async () => {
      try {
        return await appointmentApi.fetchRequests();
      } catch (err) {
        return store.appointmentRequests;
      }
    }
  });
};

export const useApproveRequest = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async ({ id, therapistId, duration }: { id: string; therapistId?: string; duration?: number }) => {
      try {
        await appointmentApi.approveRequest(id, therapistId, duration);
      } catch (err) {
        store.approveRequest(id, therapistId, duration);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointmentRequests'] });
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Booking request approved.');
    }
  });
};

export const useRejectRequest = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (id: string) => {
      try {
        await appointmentApi.rejectRequest(id);
      } catch (err) {
        store.rejectRequest(id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointmentRequests'] });
      toast.success('Booking request rejected.');
    }
  });
};
