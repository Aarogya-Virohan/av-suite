// Mirrors backend/app/schemas/psychosocial.py. Keep the two in step.

export type InstrumentId = 'phq9' | 'gad7' | 'dass21';
export type SessionStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';
export type AssignmentStatus = 'active' | 'expired' | 'completed' | 'cancelled';

export interface Option {
  value: number;
  label: string;
}

export interface Item {
  id: string;
  number: number;
  text: string;
  scored: boolean;
  options: Option[] | null;
}

export interface Instrument {
  id: InstrumentId;
  version: string;
  short_name: string;
  name: string;
  instructions: string;
  options: Option[];
  items: Item[];
  licence_note: string;
}

export interface InstrumentSummary {
  id: InstrumentId;
  version: string;
  short_name: string;
  name: string;
  item_count: number;
  citation: string;
}

export interface Scale {
  scale_id: string;
  label: string;
  score: number;
  max_score: number;
  band_label: string;
  band_level: number;
  referral: boolean;
}

export interface SessionSummary {
  id: string;
  assignment_id: string;
  patient_id: string;
  instrument_id: InstrumentId;
  instrument_version: string;
  short_name: string;
  position: number;
  status: SessionStatus;
  answered_count: number;
  total_items: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  referral_flag: boolean;
  risk_item_flag: boolean;
  partial_risk: boolean;
  scales: Scale[];
}

export interface Assignment {
  id: string;
  patient_id: string;
  status: 'active' | 'completed' | 'cancelled';
  effective_status: AssignmentStatus;
  expires_at: string;
  created_at: string;
  assigned_by_name: string | null;
  sessions: SessionSummary[];
}

export interface AssignmentCreated {
  assignment: Assignment;
  screener_path: string;
}

export interface WorklistRow {
  session: SessionSummary;
  patient_name: string;
  assignment_effective_status: AssignmentStatus;
}

export interface ResponseRow {
  item_id: string;
  number: number;
  text: string;
  scored: boolean;
  value: number | null;
  answer_label: string | null;
}

export interface ReferralAction {
  id: string;
  session_id: string;
  action: ReferralActionKey;
  note: string | null;
  recorded_by_name: string | null;
  recorded_at: string;
}

export type ReferralActionKey =
  | 'referred_gp'
  | 'referred_psychologist'
  | 'referred_psychiatrist'
  | 'already_under_care'
  | 'patient_declined'
  | 'monitor_and_rescreen'
  | 'other';

export interface SessionDetail {
  session: SessionSummary;
  patient_name: string;
  instrument_name: string;
  citation: string;
  reasons: string[];
  responses: ResponseRow[];
  baseline: { session_id: string; completed_at: string | null; scales: Scale[] } | null;
  is_baseline: boolean;
  referral_actions: ReferralAction[];
}

export interface PatientSummary {
  patient_id: string;
  referral_flag: boolean;
  risk_item_flag: boolean;
  latest: SessionSummary[];
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  age: number | null;
  date_of_birth: string | null;
  gender: string | null;
  status: string;
}

export interface Me {
  user: { id: string; email: string; name: string; role: string };
  active_workspace: { clinic_id: string; name: string; role: string } | null;
  active_products: { key: string; status: string }[];
  capabilities: string[];
}

export interface ClinicUser {
  id: string;
  name: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
  role: string;
  is_active: boolean;
}

export interface PermissionOverride {
  capability_key: string;
  scope: 'none' | 'own' | 'all';
}

// Public screener
export interface ScreenerQuestionnaire {
  instrument: Instrument;
  status: SessionStatus;
  answers: Record<string, number>;
}

export interface ScreenerState {
  clinic_name: string;
  expires_at: string;
  consent: { required: boolean; text_version: string; title: string; paragraphs: string[] };
  questionnaires: ScreenerQuestionnaire[];
  current_instrument_id: InstrumentId | null;
}

export interface SubmitResult {
  instrument_id: InstrumentId;
  assignment_complete: boolean;
  next_instrument_id: InstrumentId | null;
  show_referral_message: boolean;
  show_support_contacts: boolean;
}

// Deletion on request (SRS 3.2). Counts only, never results.
export interface ScreeningData {
  patient_id: string;
  links: number;
  screeners: number;
  referral_actions: number;
  consent_records: number;
  withdrawal_on_file: boolean;
}
