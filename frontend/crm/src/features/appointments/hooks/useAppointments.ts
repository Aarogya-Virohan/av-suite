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
      const data = await appointmentApi.fetch();
      const latency = Date.now() - startTime;
      localStorage.setItem('api_last_latency', `${latency}ms`);
      return data;
    }
  });
};

export const useCreateAppointment = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (data: AppointmentInput) => {
      return await appointmentApi.create(data);
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
      return await appointmentApi.updateStatus(id, status);
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
      await appointmentApi.delete(id);
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
      return await appointmentApi.fetchRequests();
    }
  });
};

export const useApproveRequest = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

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
    }
  });
};

export const useRejectRequest = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (id: string) => {
      await appointmentApi.rejectRequest(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['appointmentRequests'] });
      toast.success('Booking request rejected.');
    }
  });
};
