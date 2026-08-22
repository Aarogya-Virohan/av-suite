import { z } from 'zod';

export const patientStatusSchema = z.enum(['active', 'inactive', 'discharged']);
export const leadStageSchema = z.enum(['new', 'contacted', 'qualified', 'converted', 'lost']);
export const leadSourceSchema = z.enum(['website', 'referral', 'social_media', 'walk_in', 'advertisement', 'other']);
export const appointmentStatusSchema = z.enum(['scheduled', 'completed', 'cancelled', 'no_show']);
export const appointmentSourceSchema = z.enum(['manual', 'public_booking']);
export const packageStatusSchema = z.enum(['active', 'inactive', 'completed', 'expired', 'cancelled']);
export const invoiceStatusSchema = z.enum(['unpaid', 'paid', 'partial', 'draft', 'issued', 'cancelled', 'overdue']);
export const paymentMethodSchema = z.enum(['cash', 'upi', 'card', 'bank_transfer', 'insurance', 'other']);
export const paymentStatusSchema = z.enum(['completed', 'voided']);
export const documentCategorySchema = z.enum(['medical_report', 'prescription', 'lab_result', 'consent', 'other']);
export const genderSchema = z.enum(['male', 'female', 'other']);

// Patient Form Schema
export const patientFormSchema = z.object({
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().min(1, 'Last name is required'),
  date_of_birth: z.string().nullable().optional(),
  phone: z.string().min(10, 'Phone number must be at least 10 digits'),
  gender: genderSchema,
  chief_complaint: z.string().min(1, 'Chief complaint is required'),
  referral_source: z.string().min(1, 'Referral source is required'),
  status: patientStatusSchema,
});
export type PatientFormValues = z.infer<typeof patientFormSchema>;

// Lead Form Schema
export const leadFormSchema = z.object({
  name: z.string().min(1, 'Lead name is required'),
  phone: z.string().min(10, 'Phone number must be at least 10 digits'),
  email: z.string().email('Invalid email address').nullable().optional().or(z.literal('')),
  source: leadSourceSchema,
  stage: leadStageSchema,
  assigned_to: z.string().nullable().optional(),
  notes: z.string(),
});
export type LeadFormValues = z.infer<typeof leadFormSchema>;

// Appointment Form Schema
export const appointmentFormSchema = z.object({
  patient_id: z.string().min(1, 'Patient selection is required'),
  therapist_id: z.string().min(1, 'Therapist selection is required'),
  appointment_type: z.string(),
  scheduled_at: z.string().min(1, 'Schedule date/time is required'),
  duration_minutes: z.number().min(15),
  status: appointmentStatusSchema,
  source: appointmentSourceSchema,
});
export type AppointmentFormValues = z.infer<typeof appointmentFormSchema>;

// Treatment Session Form Schema
export const treatmentSessionFormSchema = z.object({
  patient_id: z.string().min(1, 'Patient ID is required'),
  appointment_id: z.string().nullable().optional(),
  therapist_id: z.string().min(1, 'Therapist ID is required'),
  treatment_date: z.string().min(1, 'Treatment date is required'),
  pain_score: z.number().min(0).max(10).nullable().optional(),
  treatment: z.string().min(1, 'Treatment description is required'),
  home_advice: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
});
export type TreatmentSessionFormValues = z.infer<typeof treatmentSessionFormSchema>;

// SOAP Assessment Form Schema
export const soapAssessmentFormSchema = z.object({
  patient_id: z.string().min(1, 'Patient ID is required'),
  appointment_id: z.string().nullable().optional(),
  author_id: z.string().min(1, 'Author ID is required'),
  specialty: z.string().min(1, 'Specialty is required'),
  diagnosis: z.string().nullable().optional(),
  is_reassessment: z.boolean(),
  form_data: z.record(z.string(), z.unknown()),
});
export type SoapAssessmentFormValues = z.infer<typeof soapAssessmentFormSchema>;

// Invoice Item Schema
export const invoiceItemSchema = z.object({
  description: z.string().min(1, 'Description is required'),
  quantity: z.number().min(1),
  unit_price: z.number().min(0, 'Unit price must be >= 0'),
  total_price: z.number().min(0),
});
export type InvoiceItemValues = z.infer<typeof invoiceItemSchema>;

// Invoice Form Schema
export const invoiceFormSchema = z.object({
  patient_id: z.string().min(1, 'Patient selection is required'),
  appointment_id: z.string().nullable().optional(),
  issue_date: z.string().min(1, 'Issue date is required'),
  due_date: z.string().nullable().optional(),
  subtotal: z.number().min(0),
  discount_amount: z.number().min(0),
  tax_amount: z.number().min(0),
  total_amount: z.number().min(0),
  notes: z.string(),
  items: z.array(invoiceItemSchema).min(1, 'At least one line item is required'),
});
export type InvoiceFormValues = z.infer<typeof invoiceFormSchema>;

// Payment Form Schema
export const paymentFormSchema = z.object({
  invoice_id: z.string().min(1, 'Invoice ID is required'),
  patient_id: z.string().min(1, 'Patient ID is required'),
  amount: z.number().min(1, 'Amount must be greater than 0'),
  payment_method: paymentMethodSchema,
  payment_date: z.string().min(1, 'Payment date is required'),
  transaction_reference: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
});
export type PaymentFormValues = z.infer<typeof paymentFormSchema>;

// Patient Document Form Schema
export const patientDocumentFormSchema = z.object({
  patient_id: z.string().min(1, 'Patient ID is required'),
  uploaded_by: z.string().nullable().optional(),
  treatment_id: z.string().nullable().optional(),
  label: z.string().min(1, 'Document label is required'),
  category: documentCategorySchema,
  notes: z.string(),
});
export type PatientDocumentFormValues = z.infer<typeof patientDocumentFormSchema>;
