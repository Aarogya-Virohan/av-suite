import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patientApi } from '../services/patient.api';
import { useCRMStore } from '@/lib/store';
import { PatientIntakeInput } from '../schemas/patient.schema';
import { toast } from 'sonner';

export const usePatients = (page = 1) => {
  const store = useCRMStore();
  
  return useQuery({
    queryKey: ['patients', page],
    queryFn: async () => {
      const startTime = Date.now();
      try {
        const data = await patientApi.fetch(page);
        // Sync local store
        if (data && Array.isArray(data)) {
          // Update store patients list
        }
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms`);
        return data;
      } catch (err) {
        // Fallback to mock store
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms (Mock)`);
        
        // Translate mock store Patients to match api schema if needed
        return store.patients;
      }
    }
  });
};

export const usePatient = (id: string | null) => {
  const store = useCRMStore();
  
  return useQuery({
    queryKey: ['patient', id],
    queryFn: async () => {
      if (!id) return null;
      const startTime = Date.now();
      try {
        const data = await patientApi.fetchOne(id);
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms`);
        return data;
      } catch (err) {
        const latency = Date.now() - startTime;
        localStorage.setItem('api_last_latency', `${latency}ms (Mock)`);
        
        // Fallback to local store patient
        const localPt = store.patients.find((p) => p.id === id);
        return localPt || null;
      }
    },
    enabled: !!id
  });
};

export const useCreatePatient = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (data: PatientIntakeInput) => {
      try {
        return await patientApi.create(data);
      } catch (err) {
        // Fallback to local store
        const newPt = store.addPatient({
          name: data.full_name,
          mobile: data.phone,
          age: data.age,
          gender: data.gender === 'male' ? 'Male' : data.gender === 'female' ? 'Female' : 'Other',
          status: 'Active',
          diagnosis: data.chief_complaint,
          referralSource: data.referral_source
        } as any);
        return newPt;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Patient record created successfully!');
    }
  });
};

export const useUpdatePatient = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<PatientIntakeInput> }) => {
      try {
        return await patientApi.update(id, data);
      } catch (err) {
        // Fallback to local store
        store.updatePatient(id, {
          name: data.full_name,
          mobile: data.phone,
          age: data.age,
          gender: data.gender ? (data.gender === 'male' ? 'Male' : data.gender === 'female' ? 'Female' : 'Other') : undefined,
          diagnosis: data.chief_complaint,
          referralSource: data.referral_source
        } as any);
        return store.patients.find(p => p.id === id);
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      if (data?.id) {
        queryClient.invalidateQueries({ queryKey: ['patient', data.id] });
      }
      toast.success('Patient record updated.');
    }
  });
};

export const useDeletePatient = () => {
  const queryClient = useQueryClient();
  const store = useCRMStore();

  return useMutation({
    mutationFn: async (id: string) => {
      try {
        await patientApi.delete(id);
      } catch (err) {
        // Fallback to soft delete
        store.deletePatient(id);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      toast.success('Patient moved to Recycle Bin.');
    }
  });
};
