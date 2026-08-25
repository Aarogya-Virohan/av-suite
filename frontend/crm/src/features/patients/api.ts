import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { Patient } from '../../types/api';
import { PatientFormValues } from '../../lib/schemas';

export const PATIENTS_QUERY_KEY = ['patients'];

export function usePatients(search?: string, page = 1, page_size = 10) {
  return useQuery({
    queryKey: [...PATIENTS_QUERY_KEY, { search, page, page_size }],
    queryFn: async () => {
      const res = await apiClient.get('/patients', {
        params: { search: search || undefined, page, page_size },
      });
      return res.data as { data: Patient[]; meta: { total: number; page: number; page_size: number } };
    },
  });
}

export function usePatient(id: string) {
  return useQuery<Patient | null>({
    queryKey: [...PATIENTS_QUERY_KEY, id],
    queryFn: async () => {
      const res = await apiClient.get(`/patients/${id}`);
      return res.data?.data || res.data || null;
    },
    enabled: !!id,
  });
}

export function useCreatePatient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (values: PatientFormValues) => {
      const res = await apiClient.post('/patients', values);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
    },
  });
}

export function useUpdatePatient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, values }: { id: string; values: Partial<PatientFormValues> }) => {
      const res = await apiClient.patch(`/patients/${id}`, values);
      return res.data?.data || res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
    },
  });
}

export function useDeletePatient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiClient.delete(`/patients/${id}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PATIENTS_QUERY_KEY });
    },
  });
}

export const PATIENT_DOCUMENTS_QUERY_KEY = ['patient-documents'];

export function usePatientDocuments(patientId: string) {
  return useQuery({
    queryKey: [...PATIENT_DOCUMENTS_QUERY_KEY, patientId],
    queryFn: async () => {
      const res = await apiClient.get(`/patients/${patientId}/documents`);
      return res.data as { data: any[]; meta: any };
    },
    enabled: !!patientId,
  });
}

export function useUploadPatientDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      patientId,
      payload,
    }: {
      patientId: string;
      payload: {
        patient_id: string;
        label: string;
        category: string;
        file_url: string;
        file_type: string;
        file_size: number;
        notes?: string;
        treatment_id?: string | null;
      };
    }) => {
      const res = await apiClient.post(`/patients/${patientId}/documents`, payload);
      return res.data?.data || res.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: [...PATIENT_DOCUMENTS_QUERY_KEY, variables.patientId],
      });
    },
  });
}
