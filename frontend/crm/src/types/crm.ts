export type UserRole = 'admin' | 'therapist' | 'front_desk';

export type PatientStatus = 'Active' | 'Inactive' | 'Discharged';

export type LeadStage = 'New Lead' | 'Contacted' | 'Appointment Booked' | 'Converted' | 'Lost';

export type AppointmentStatus = 'Scheduled' | 'Confirmed' | 'Completed' | 'Cancelled' | 'No Show';

export type AppointmentRequestStatus = 'Pending' | 'Approved' | 'Rejected';

export type InvoiceStatus = 'Paid' | 'Partial' | 'Due';

export type PaymentMode = 'Cash' | 'UPI' | 'Card' | 'Bank Transfer';

export type SpecialtyKey = 'ortho' | 'neuro' | 'cardiopulm' | 'sports' | 'paeds' | 'general';

export interface ClinicBranding {
  clinicName: string;
  phone: string;
  address: string;
  doctorName: string;
  regNo: string;
  brandColor: string;
  logoBase64?: string;
  apiUrl?: string;
  bookingUrl?: string;
}

export interface Therapist {
  id: string;
  name: string;
  specialization?: string;
  mobile?: string;
  email?: string;
  regNo?: string;
  salary?: number;
  qualification?: string;
  notes?: string;
}

export interface Patient {
  id: string;
  clinicId: string;
  name: string;
  mobile: string;
  age?: number;
  gender?: 'Male' | 'Female' | 'Other';
  email?: string;
  address?: string;
  referralSource?: string;
  status: PatientStatus;
  diagnosis?: string;
  medicalHistory?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface Lead {
  id: string;
  clinicId: string;
  name: string;
  mobile?: string;
  source: string;
  stage: LeadStage;
  notes?: string;
  convertedPatientId?: string;
  createdAt: string;
}

export interface Appointment {
  id: string;
  clinicId: string;
  patientId: string;
  patientName: string;
  patientMobile?: string;
  therapist?: string;
  date: string;
  time: string;
  durationMinutes: number;
  status: AppointmentStatus;
  source: 'manual' | 'public_booking';
  notes?: string;
  createdAt: string;
}

export interface AppointmentRequest {
  id: string;
  clinicId: string;
  name: string;
  mobile: string;
  age?: number;
  gender?: string;
  preferredDate: string;
  preferredTime: string;
  chiefComplaint?: string;
  source?: string;
  refId?: string;
  status: AppointmentRequestStatus;
  createdAt: string;
}

export interface SOAPAssessment {
  id: string;
  clinicId: string;
  patientId: string;
  diagnosis?: string;
  specialty: SpecialtyKey;
  isReassessment: boolean;
  formData: Record<string, string>;
  createdAt: string;
}

export interface TreatmentSession {
  id: string;
  clinicId: string;
  patientId: string;
  date: string;
  therapist?: string;
  painScore?: number;
  treatment: string;
  homeAdvice?: string;
  notes?: string;
  createdAt: string;
}

export interface PackageCatalog {
  id: string;
  clinicId: string;
  packageName: string;
  totalSessions: number;
  amount: number;
  validityDays?: number;
  notes?: string;
}

export interface PatientPackage {
  id: string;
  clinicId: string;
  patientId: string;
  patientName?: string;
  packageName: string;
  totalSessions: number;
  sessionsUsed: number;
  amount: number;
  startDate: string;
  validTill?: string;
  status: 'Active' | 'Expired';
  createdAt: string;
}

export interface InvoiceLineItem {
  description: string;
  amount: number;
}

export interface Invoice {
  id: string;
  clinicId: string;
  patientId: string;
  patientName: string;
  description: string;
  amount: number; // Base amount
  tax: number; // GST Amount
  discount: number;
  total: number;
  paidAmount: number;
  status: InvoiceStatus;
  date: string;
  createdAt: string;
}

export interface Payment {
  id: string;
  clinicId: string;
  invoiceId: string;
  patientId: string;
  amount: number;
  mode: PaymentMode;
  reference?: string;
  date: string;
}

export interface PatientDocument {
  id: string;
  clinicId: string;
  patientId: string;
  fileName: string;
  category: 'General' | 'Lab Report' | 'Imaging' | 'Referral Letter' | 'ID Proof' | 'Prescription';
  url: string;
  createdAt: string;
}

export interface AuditLog {
  id: string;
  clinicId: string;
  action: string;
  entityType: 'patient' | 'appointment' | 'invoice' | 'lead' | 'treatment';
  entityId: string;
  description: string;
  createdAt: string;
}

export interface RecycleBinItem {
  id: string;
  type: 'patients' | 'appointments' | 'invoices' | 'leads';
  data: any;
  deletedAt: string;
}

export interface RunningCost {
  id: string;
  label: string;
  amount: number;
}
