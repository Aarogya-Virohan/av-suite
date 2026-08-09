import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { appointmentApi } from '../services/appointment.api';

import { AppointmentInput } from '../schemas/appointment.schema';
import { toast } from 'sonner';

export const useAppointments = () => {
  return useQuery({
    queryKey: ['appointments'],
    queryFn: async () => {
      const startTime = Date.now();
      const data = await appointmentApi.fetch();
      const latency = Date.now() - startTime;
      localStorage.setItem('api_last_latency', `${latency}ms`);
      return data;
    }
  });
};

export const useCreateAppointment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AppointmentInput) => {
      return await appointmentApi.create(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      toast.success('Appointment booked successfully!');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to book appointment.');
    }
  });
};

export const useUpdateAppointmentStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      return await appointmentApi.updateStatus(id, status);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      toast.success('Appointment status updated.');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to update appointment status.');
    }
  });
};

export const useDeleteAppointment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await appointmentApi.delete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      toast.success('Appointment moved to Recycle Bin.');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to delete appointment.');
    }
  });
};

export const useAppointmentRequests = () => {
  return useQuery({
    queryKey: ['appointmentRequests'],
    queryFn: async () => {
      return await appointmentApi.fetchRequests();
    }
  });
};

export const useApproveRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, therapistId, duration }: { id: string; therapistId?: string; duration?: number }) => {
      await appointmentApi.approveRequest(id, therapistId, duration);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointmentRequests'] });
      queryClient.invalidateQueries({ queryKey: ['appointments'] });
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Booking request approved.');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to approve booking request.');
    }
  });
};

export const useRejectRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await appointmentApi.rejectRequest(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointmentRequests'] });
      toast.success('Booking request rejected.');
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.message || err.message || 'Failed to reject booking request.');
    }
  });
};
