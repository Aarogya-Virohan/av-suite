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
}

export interface PrescriptionItem {
  exercise: Exercise;
  sets: number;
  reps: number;
  hold: number;
  frequency: string;
}
