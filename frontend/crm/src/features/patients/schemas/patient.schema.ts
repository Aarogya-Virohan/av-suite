import { z } from 'zod';

export const patientIntakeSchema = z.object({
  full_name: z.string().min(1, 'Patient Name is required'),
  phone: z.string().regex(/^\d{10}$/, 'Phone must be exactly 10 digits'),
  age: z.number().int().min(1, 'Age must be at least 1').max(120, 'Age cannot exceed 120'),
  gender: z.literal('male').or(z.literal('female')).or(z.literal('other')),
  chief_complaint: z.string().min(1, 'Primary complaint is required'),
  referral_source: z.string().optional()
});

export type PatientIntakeInput = z.infer<typeof patientIntakeSchema>;
