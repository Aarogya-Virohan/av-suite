import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { useAuthStore } from '../../store';

/** Clinic profile printed on invoices and receipts (D-026). All optional. */
export interface ClinicProfile {
  address_line: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  phone: string | null;
  email: string | null;
  registration_number: string | null;
  gstin: string | null;
  authorised_person: string | null;
}

export const CLINIC_PROFILE_KEYS: (keyof ClinicProfile)[] = [
  'address_line',
  'city',
  'state',
  'pincode',
  'phone',
  'email',
  'registration_number',
  'gstin',
  'authorised_person',
];

export interface ClinicSettings extends Partial<ClinicProfile> {
  id: string;
  name: string;
  branding_logo_url: string | null;
  branding_color: string | null;
  plan_tier: string;
  is_partner_clinic: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicSettingsUpdate extends Partial<ClinicProfile> {
  name?: string | null;
  branding_logo_url?: string | null;
  branding_color?: string | null;
}

export const useClinicSettings = (enabled = true) => {
  return useQuery({
    queryKey: ['clinic-settings'],
    queryFn: async () => {
      const res = await apiClient.get('/settings/clinic');
      return (res.data?.data || res.data) as ClinicSettings;
    },
    enabled,
  });
};

export const useUpdateClinicSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (values: ClinicSettingsUpdate) => {
      const res = await apiClient.patch('/settings/clinic', values);
      return (res.data?.data || res.data) as ClinicSettings;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clinic-settings'] });
      // Invoices read the clinic from /auth/me, so refresh it after a change.
      void useAuthStore.getState().fetchMe();
    },
  });
};
