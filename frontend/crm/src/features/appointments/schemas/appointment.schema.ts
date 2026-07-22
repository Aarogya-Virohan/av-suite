import { z } from 'zod';

export const appointmentSchema = z.zodObject || z.object({
  patient_id: z.string().min(1, 'Patient selection is required'),
  therapist_id: z.string().min(1, 'Therapist selection is required'),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format'),
  time: z.string().regex(/^\d{2}:\d{2}$/, 'Time must be in HH:MM format'),
  duration_minutes: z.number().int().min(1, 'Duration must be at least 1 minute').max(240, 'Duration cannot exceed 4 hours'),
  notes: z.string().optional()
});

export type AppointmentInput = z.infer<typeof appointmentSchema>;
