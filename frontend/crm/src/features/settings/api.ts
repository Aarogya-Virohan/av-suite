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
  /** Doctor name in the clinical report header; empty = clinic owner admin's name (BR-h). */
  display_doctor_name: string | null;
  /** Shown in the clinic block above the clinical report footer (BR-i). */
  website: string | null;
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
  'display_doctor_name',
  'website',
];

/** How the logo background shows on the report band (BR-b). Exactly one. */
export type LogoBgMode = 'as_is' | 'white' | 'transparent';

export const LOGO_BG_OPTIONS: { value: LogoBgMode; label: string; hint: string }[] = [
  { value: 'as_is', label: 'As uploaded', hint: 'The logo exactly as the file is.' },
  { value: 'white', label: 'White background', hint: 'The logo sits on a small white tile.' },
  { value: 'transparent', label: 'Background removed', hint: 'A plain background around the logo is taken out.' },
];

export const LOGO_HELPER_TEXT =
  'PNG, JPG or WebP, up to 2 MB. At least 200 px on the shorter side. A transparent PNG gives the cleanest result.';

export const LOGO_UPLOAD_MAX_BYTES = 2 * 1024 * 1024;
export const LOGO_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

export interface LogoPreview {
  /** The resized copy the server would store. */
  logo: string;
  /** The logo as the report band shows it in the chosen mode. */
  letterhead_logo: string;
  width: number;
  height: number;
  low_contrast: boolean;
}

/** Checks a picked logo against the upload rules and returns the band preview. Saves nothing. */
export async function previewLogo(logo: string, mode: LogoBgMode): Promise<LogoPreview> {
  const res = await apiClient.post('/settings/clinic/logo-preview', { logo, logo_bg_mode: mode });
  return (res.data?.data || res.data) as LogoPreview;
}

/** Kind of client; set in Settings, sent back by /settings/clinic and /auth/me. */
export type ClientType = 'clinic' | 'hospital' | 'home_care';

export const CLIENT_TYPE_OPTIONS: { value: ClientType; label: string }[] = [
  { value: 'clinic', label: 'Clinic' },
  { value: 'hospital', label: 'Hospital' },
  { value: 'home_care', label: 'Home care' },
];

export interface ClinicSettings extends Partial<ClinicProfile> {
  id: string;
  name: string;
  /** Prefix of the Patient ID, e.g. "ADP" in ADP-000003. */
  code: string;
  client_type?: ClientType;
  branding_logo_url: string | null;
  branding_color: string | null;
  logo_bg_mode?: LogoBgMode;
  /** The saved logo is hard to see on the report band in the saved mode. */
  logo_low_contrast?: boolean;
  plan_tier: string;
  is_partner_clinic: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicSettingsUpdate extends Partial<ClinicProfile> {
  name?: string | null;
  code?: string;
  client_type?: ClientType;
  branding_logo_url?: string | null;
  branding_color?: string | null;
  logo_bg_mode?: LogoBgMode;
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
