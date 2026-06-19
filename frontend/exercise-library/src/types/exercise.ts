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
}

export interface PrescriptionItem {
  exercise: Exercise;
  sets: number;
  reps: number;
  hold: number;
  frequency: string;
  note?: string;
}

