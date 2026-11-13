import type { ClinicProfile } from './api';

export type ProfileForm = Record<keyof ClinicProfile, string>;

export const EMPTY_PROFILE: ProfileForm = {
  address_line: '',
  city: '',
  state: '',
  pincode: '',
  phone: '',
  email: '',
  registration_number: '',
  gstin: '',
  authorised_person: '',
};

/* Printed on invoices and receipts (D-026). Lengths match the database columns. */
export const PROFILE_FIELDS: { key: keyof ClinicProfile; label: string; max: number; placeholder?: string; wide?: boolean; type?: string }[] = [
  { key: 'address_line', label: 'Address', max: 500, placeholder: 'Building, street, area', wide: true },
  { key: 'city', label: 'City', max: 120 },
  { key: 'state', label: 'State', max: 120 },
  { key: 'pincode', label: 'PIN code', max: 6, placeholder: '6 digits' },
  { key: 'phone', label: 'Clinic phone', max: 50, type: 'tel' },
  { key: 'email', label: 'Clinic email', max: 255, type: 'email' },
  { key: 'registration_number', label: 'Registration number', max: 120 },
  { key: 'gstin', label: 'GSTIN', max: 15, placeholder: '15 characters' },
  { key: 'authorised_person', label: 'Authorised person', max: 255, placeholder: 'Name printed on invoices' },
];

/** Same checks as the API: PIN code 6 digits, GSTIN 15 characters, email format. */
export function clinicProfileErrors(form: ProfileForm): Partial<Record<keyof ClinicProfile, string>> {
  const errors: Partial<Record<keyof ClinicProfile, string>> = {};
  const pin = form.pincode.trim();
  const gstin = form.gstin.trim();
  const email = form.email.trim();
  if (pin && !/^\d{6}$/.test(pin)) errors.pincode = 'PIN code must be 6 digits';
  if (gstin && gstin.length !== 15) errors.gstin = 'GSTIN must be 15 characters';
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = 'Enter a valid email';
  return errors;
}
