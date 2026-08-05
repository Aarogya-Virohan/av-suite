export type UserRole = 'admin' | 'therapist' | 'front_desk' | 'patient';

export type PatientStatus = 'active' | 'inactive' | 'discharged';
export type LeadStage = 'new' | 'contacted' | 'qualified' | 'converted' | 'lost';
export type AppointmentStatus = 'scheduled' | 'completed' | 'cancelled' | 'no_show';
export type AppointmentSource = 'manual' | 'public_booking';
export type PackageStatus = 'active' | 'inactive' | 'completed' | 'expired' | 'cancelled';
export type InvoiceStatus = 'unpaid' | 'paid' | 'partial' | 'draft' | 'issued' | 'cancelled';
export type PaymentMethod = 'cash' | 'upi' | 'card' | 'bank_transfer' | 'insurance' | 'other';
export type PaymentStatus = 'completed' | 'voided';
export type DocumentCategory = 'medical_report' | 'prescription' | 'lab_result' | 'consent' | 'other';

export interface User {
  id: string;
  clinic_id: string;
  email: string;
  role: UserRole;
  first_name: string;
  last_name: string;
  phone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Patient {
  id: string;
  clinic_id: string;
  user_id: string | null;
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  phone: string;
  gender: string;
  chief_complaint: string;
  referral_source: string;
  status: PatientStatus;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
}

export interface Lead {
  id: string;
  clinic_id: string;
  name: string;
  phone: string;
  email: string | null;
  source: string;
  stage: LeadStage;
  assigned_to: string | null;
  notes: string;
  converted_patient_id: string | null;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  deleted_by?: string | null;
}

export interface Appointment {
  id: string;
  clinic_id: string;
  patient_id: string;
  therapist_id: string;
  appointment_type: string;
  scheduled_at: string;
  duration_minutes: number;
  status: AppointmentStatus;
  source: AppointmentSource;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  deleted_by?: string | null;
}

export interface TreatmentSession {
  id: string;
  clinic_id: string;
  patient_id: string;
  appointment_id: string | null;
  therapist_id: string;
  treatment_date: string;
  pain_score: number | null;
  treatment: string;
  home_advice: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SoapAssessment {
  id: string;
  clinic_id: string;
  patient_id: string;
  appointment_id: string | null;
  author_id: string;
  specialty: string;
  diagnosis: string | null;
  is_reassessment: boolean;
  form_data: Record<string, unknown>;
  finalized_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Package {
  id: string;
  clinic_id: string;
  name: string;
  total_sessions: number;
  price: number;
  validity_days: number;
  status: PackageStatus;
  created_at: string;
  updated_at: string;
}

export interface PatientPackage {
  id: string;
  clinic_id: string;
  patient_id: string;
  package_id: string | null;
  package_name: string;
  total_sessions: number;
  completed_sessions: number;
  price: number;
  status: PackageStatus;
  purchased_at: string;
  expires_at: string;
  created_at: string;
  updated_at: string;
}

export interface Invoice {
  id: string;
  clinic_id: string;
  patient_id: string;
  appointment_id: string | null;
  invoice_number: string;
  issue_date: string;
  due_date: string | null;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  total_amount: number;
  paid_amount: number;
  status: InvoiceStatus;
  notes: string;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  deleted_by?: string | null;
}

export interface InvoiceItem {
  id: string;
  clinic_id: string;
  invoice_id: string;
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  clinic_id: string;
  invoice_id: string;
  patient_id: string;
  amount: number;
  payment_method: PaymentMethod;
  status: PaymentStatus;
  payment_date: string;
  transaction_reference: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientDocument {
  id: string;
  clinic_id: string;
  patient_id: string;
  uploaded_by: string | null;
  treatment_id: string | null;
  file_url: string;
  file_type: string;
  file_size: number | null;
  label: string;
  category: DocumentCategory;
  notes: string;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
  deleted_by?: string | null;
}

export interface AuditLog {
  id: string;
  clinic_id: string;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AnalyticsOverview {
  total_patients: number;
  active_appointments_today: number;
  monthly_revenue: number;
  pending_leads: number;
  revenue_trend: Array<{ date: string; amount: number }>;
}
