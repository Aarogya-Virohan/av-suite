export interface Exercise {
  id: string;
  name: string;
  bodyPart: string;
  condition: string;
  instructions: string;
  sets: number;
  reps: number;
  hold: number;
  frequency: string;
  isFree: boolean;
  videoUrl?: string;
  imageUrl?: string;
  /** The clinic's own photos of this exercise (front, side). */
  photos?: ExercisePhoto[];
  /** Part of the AV library (no clinic). Clinics cannot change it (EL-D-008). */
  isGlobal?: boolean;
  /** Ids of the categories the exercise carries (EL-D-005). */
  categoryIds?: string[];
}

export type PhotoAngle = "front" | "side";

export interface ExercisePhoto {
  angle: PhotoAngle;
  /** Changes on every upload; used to refresh a cached copy. */
  updatedAt: string;
}

export interface PrescriptionItem {
  exercise: Exercise;
  sets: number;
  reps: number;
  hold: number;
  frequency: string;
  note?: string;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  phone?: string | null;
  date_of_birth?: string | null;
}

/** A prescription as GET /prescriptions returns it. */
export interface SavedPrescription {
  id: string;
  patient_id: string;
  physio_notes?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  items: Array<{
    exercise_id: string;
    sets: number;
    reps: number;
    hold: number;
    frequency: string;
    note?: string | null;
    exercise?: Record<string, unknown> | null;
  }>;
}
