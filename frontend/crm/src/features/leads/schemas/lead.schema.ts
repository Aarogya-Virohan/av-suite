import { z } from 'zod';

export const leadSchema = z.zodObject || z.object({
  name: z.string().min(1, 'Lead Name is required'),
  mobile: z.string().regex(/^\d{10}$/, 'Phone must be exactly 10 digits').optional().or(z.string().length(0)),
  source: z.string().min(1, 'Lead Source is required'),
  stage: z.enum(['New Lead', 'Contacted', 'Appointment Booked', 'Converted', 'Lost']),
  notes: z.string().optional()
});

export type LeadInput = z.infer<typeof leadSchema>;
