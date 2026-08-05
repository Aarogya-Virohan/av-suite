import {
  Patient,
  Lead,
  Appointment,
  TreatmentSession,
  SoapAssessment,
  Package,
  PatientPackage,
  Invoice,
  InvoiceItem,
  Payment,
  PatientDocument,
  AuditLog,
  User,
  AnalyticsOverview,
} from '../types/api';

export const mockUsers: User[] = [
  {
    id: 'usr_admin_1',
    clinic_id: 'cln_aarogya_1',
    email: 'admin@aarogya.com',
    role: 'admin',
    first_name: 'Tarun',
    last_name: 'Sharma',
    phone: '+919876543210',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'usr_therapist_1',
    clinic_id: 'cln_aarogya_1',
    email: 'therapist@aarogya.com',
    role: 'therapist',
    first_name: 'Ananya',
    last_name: 'Roy',
    phone: '+919876543211',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'usr_desk_1',
    clinic_id: 'cln_aarogya_1',
    email: 'desk@aarogya.com',
    role: 'front_desk',
    first_name: 'Rohan',
    last_name: 'Verma',
    phone: '+919876543212',
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

export const mockPatients: Patient[] = [
  {
    id: 'pat_1',
    clinic_id: 'cln_aarogya_1',
    user_id: null,
    first_name: 'Rajesh',
    last_name: 'Kumar',
    date_of_birth: '1985-05-15',
    phone: '+919811122233',
    gender: 'male',
    chief_complaint: 'Lower back stiffness and lumbo-sacral pain',
    referral_source: 'Google Search',
    status: 'active',
    created_at: '2026-07-01T10:00:00Z',
    updated_at: '2026-07-01T10:00:00Z',
  },
  {
    id: 'pat_2',
    clinic_id: 'cln_aarogya_1',
    user_id: null,
    first_name: 'Priya',
    last_name: 'Sharma',
    date_of_birth: '1992-11-20',
    phone: '+919822233344',
    gender: 'female',
    chief_complaint: 'Cervical spondylosis post office work',
    referral_source: 'Doctor Referral',
    status: 'active',
    created_at: '2026-07-05T14:30:00Z',
    updated_at: '2026-07-05T14:30:00Z',
  },
];

export const mockLeads: Lead[] = [
  {
    id: 'lead_1',
    clinic_id: 'cln_aarogya_1',
    name: 'Amit Patel',
    phone: '+919988776655',
    email: 'amit.patel@example.com',
    source: 'Website Form',
    stage: 'new',
    assigned_to: 'usr_desk_1',
    notes: 'Interested in sports injury rehabilitation',
    converted_patient_id: null,
    created_at: '2026-08-01T09:00:00Z',
    updated_at: '2026-08-01T09:00:00Z',
  },
];

export const mockAppointments: Appointment[] = [
  {
    id: 'apt_1',
    clinic_id: 'cln_aarogya_1',
    patient_id: 'pat_1',
    therapist_id: 'usr_therapist_1',
    appointment_type: 'consultation',
    scheduled_at: '2026-08-05T11:00:00Z',
    duration_minutes: 45,
    status: 'scheduled',
    source: 'manual',
    created_at: '2026-08-01T10:00:00Z',
    updated_at: '2026-08-01T10:00:00Z',
  },
];

export const mockTreatmentSessions: TreatmentSession[] = [
  {
    id: 'trt_1',
    clinic_id: 'cln_aarogya_1',
    patient_id: 'pat_1',
    appointment_id: 'apt_1',
    therapist_id: 'usr_therapist_1',
    treatment_date: '2026-08-05T11:45:00Z',
    pain_score: 6,
    treatment: 'IFT therapy applied for 15 mins followed by core stability exercises.',
    home_advice: 'Perform cat-camel stretches twice daily for 10 reps.',
    notes: 'Patient reported mild relief post session.',
    created_at: '2026-08-05T12:00:00Z',
    updated_at: '2026-08-05T12:00:00Z',
  },
];

export const mockSoapAssessments: SoapAssessment[] = [
  {
    id: 'soap_1',
    clinic_id: 'cln_aarogya_1',
    patient_id: 'pat_1',
    appointment_id: 'apt_1',
    author_id: 'usr_therapist_1',
    specialty: 'physiotherapy',
    diagnosis: 'L4-L5 lumbar disc bulge',
    is_reassessment: false,
    form_data: {
      subjective: 'Pain increases on prolonged sitting.',
      objective: 'SLR positive at 45 degrees left leg.',
      assessment: 'Acute lumbo-sacral strain.',
      plan: '10 sessions package suggested.',
    },
    finalized_at: '2026-08-05T12:30:00Z',
    created_at: '2026-08-05T12:15:00Z',
    updated_at: '2026-08-05T12:30:00Z',
  },
];

export const mockPackages: Package[] = [
  {
    id: 'pkg_1',
    clinic_id: 'cln_aarogya_1',
    name: '10-Session Rehab Plan',
    total_sessions: 10,
    price: 8000,
    validity_days: 60,
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

export const mockPatientPackages: PatientPackage[] = [
  {
    id: 'ppkg_1',
    clinic_id: 'cln_aarogya_1',
    patient_id: 'pat_1',
    package_id: 'pkg_1',
    package_name: '10-Session Rehab Plan',
    total_sessions: 10,
    completed_sessions: 2,
    price: 8000,
    status: 'active',
    purchased_at: '2026-07-02T10:00:00Z',
    expires_at: '2026-08-31T23:59:59Z',
    created_at: '2026-07-02T10:00:00Z',
    updated_at: '2026-08-05T12:00:00Z',
  },
];

export const mockInvoices: Invoice[] = [
  {
    id: 'inv_1',
    clinic_id: 'cln_aarogya_1',
    patient_id: 'pat_1',
    appointment_id: 'apt_1',
    invoice_number: 'INV-2026-0001',
    issue_date: '2026-07-02',
    due_date: '2026-07-02',
    subtotal: 8000,
    discount_amount: 500,
    tax_amount: 0,
    total_amount: 7500,
    paid_amount: 7500,
    status: 'paid',
    notes: 'Package deal applied',
    created_at: '2026-07-02T10:05:00Z',
    updated_at: '2026-07-02T10:10:00Z',
  },
];

export const mockInvoiceItems: InvoiceItem[] = [
  {
    id: 'inv_item_1',
    clinic_id: 'cln_aarogya_1',
    invoice_id: 'inv_1',
    description: '10-Session Rehab Plan',
    quantity: 1,
    unit_price: 8000,
    total_price: 8000,
    created_at: '2026-07-02T10:05:00Z',
    updated_at: '2026-07-02T10:05:00Z',
  },
];

export const mockPayments: Payment[] = [
  {
    id: 'pay_1',
    clinic_id: 'cln_aarogya_1',
    invoice_id: 'inv_1',
    patient_id: 'pat_1',
    amount: 7500,
    payment_method: 'upi',
    status: 'completed',
    payment_date: '2026-07-02',
    transaction_reference: 'UPI/628104829104',
    notes: null,
    created_at: '2026-07-02T10:10:00Z',
    updated_at: '2026-07-02T10:10:00Z',
  },
];

export const mockPatientDocuments: PatientDocument[] = [
  {
    id: 'doc_1',
    clinic_id: 'cln_aarogya_1',
    patient_id: 'pat_1',
    uploaded_by: 'usr_therapist_1',
    treatment_id: 'trt_1',
    file_url: 'https://storage.aarogya.com/docs/pat_1/lumbar_mri.pdf',
    file_type: 'application/pdf',
    file_size: 1548291,
    label: 'Lumbar Spine MRI Report',
    category: 'medical_report',
    notes: 'L4-L5 disc bulge confirmed',
    created_at: '2026-07-01T11:00:00Z',
    updated_at: '2026-07-01T11:00:00Z',
  },
];

export const mockAuditLogs: AuditLog[] = [
  {
    id: 'audit_1',
    clinic_id: 'cln_aarogya_1',
    user_id: 'usr_admin_1',
    action: 'patient.create',
    entity_type: 'patients',
    entity_id: 'pat_1',
    details: { patient_name: 'Rajesh Kumar' },
    created_at: '2026-07-01T10:00:00Z',
  },
];

export const mockAnalyticsOverview: AnalyticsOverview = {
  total_patients: 124,
  active_appointments_today: 12,
  monthly_revenue: 185000,
  pending_leads: 8,
  revenue_trend: [
    { date: '2026-08-01', amount: 15000 },
    { date: '2026-08-02', amount: 22000 },
    { date: '2026-08-03', amount: 18000 },
    { date: '2026-08-04', amount: 25000 },
    { date: '2026-08-05', amount: 12000 },
  ],
};
