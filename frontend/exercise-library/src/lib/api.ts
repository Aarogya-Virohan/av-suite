import { Exercise } from "@/types/exercise";

const BASE_URL = "http://localhost:8000";

// Helper to get auth headers with JWT token
function getHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// Map backend exercise fields to camelCase frontend model
export function mapBackendExerciseToFrontend(be: any): Exercise {
  return {
    id: be.id,
    name: be.title,
    bodyPart: be.body_part || "General",
    condition: be.condition || "General Recovery",
    instructions: be.description || "",
    sets: be.sets || 3,
    reps: be.reps || 10,
    hold: be.hold || 0,
    frequency: be.frequency || "Daily",
    isFree: be.is_free,
    videoUrl: be.video_url || "",
    imageUrl: be.video_url || "", // video_url holds image URL in current DB design
  };
}

// Fetch all exercises from backend
export async function fetchExercises(search?: string, bodyPart?: string): Promise<Exercise[]> {
  let url = `${BASE_URL}/api/v1/exercises?page_size=100`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (bodyPart) url += `&body_part=${encodeURIComponent(bodyPart)}`;

  const response = await fetch(url, { headers: getHeaders() });
  if (!response.ok) throw new Error("Failed to fetch exercises");
  const json = await response.json();
  const data = json.data || [];
  return data.map(mapBackendExerciseToFrontend);
}

// Fetch exercises filtered by condition
export async function fetchExercisesByCondition(condition: string): Promise<Exercise[]> {
  const url = `${BASE_URL}/api/v1/exercises/by-condition?condition=${encodeURIComponent(condition)}`;
  const response = await fetch(url, { headers: getHeaders() });
  if (!response.ok) throw new Error("Failed to fetch exercises by condition");
  const json = await response.json();
  const data = json.data || [];
  return data.map(mapBackendExerciseToFrontend);
}

// Fetch all patients for the authenticated clinic
export async function fetchPatients(): Promise<any[]> {
  const url = `${BASE_URL}/api/v1/patients?page_size=100`;
  const response = await fetch(url, { headers: getHeaders() });
  if (!response.ok) throw new Error("Failed to fetch patients");
  const json = await response.json();
  return json.data || [];
}

// Register a new patient inline
export async function createPatient(patient: {
  first_name: string;
  last_name: string;
  date_of_birth?: string;
  phone?: string;
}): Promise<any> {
  const url = `${BASE_URL}/api/v1/patients`;
  const response = await fetch(url, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(patient),
  });
  if (!response.ok) throw new Error("Failed to create patient");
  const json = await response.json();
  return json.data;
}

// Create a new exercise prescription
export async function createPrescription(prescription: {
  patient_id: string;
  physio_notes?: string;
  status?: string;
  items: Array<{
    exercise_id: string;
    sets: number;
    reps: number;
    hold: number;
    frequency: string;
    note?: string;
  }>;
}): Promise<any> {
  const url = `${BASE_URL}/api/v1/prescriptions`;
  const response = await fetch(url, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(prescription),
  });
  if (!response.ok) throw new Error("Failed to create prescription");
  const json = await response.json();
  return json.data;
}

// Update prescription notes or status
export async function updatePrescription(
  id: string,
  patch: { physio_notes?: string; status?: string }
): Promise<any> {
  const url = `${BASE_URL}/api/v1/prescriptions/${id}`;
  const response = await fetch(url, {
    method: "PATCH",
    headers: getHeaders(),
    body: JSON.stringify(patch),
  });
  if (!response.ok) throw new Error("Failed to update prescription");
  const json = await response.json();
  return json.data;
}

// Request PDF generation for prescription
export async function generatePrescriptionPDF(id: string): Promise<string> {
  const url = `${BASE_URL}/api/v1/prescriptions/${id}/pdf`;
  const response = await fetch(url, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!response.ok) throw new Error("Failed to generate PDF");
  const json = await response.json();
  // Return the full URL path
  const pdfUrl = json.data?.pdf_url;
  return pdfUrl.startsWith("http") ? pdfUrl : `${BASE_URL}${pdfUrl}`;
}

// Save posture diagnostic session
export async function savePostureSession(session: {
  patient_id: string;
  overall_confidence?: number;
  annotated_front_image?: string;
  annotated_back_image?: string;
  annotated_side_image?: string;
  measurements: Array<{
    param_id: string;
    raw_value: number;
    unit?: string;
    notes?: string;
    severity?: string;
    visibility?: string;
  }>;
}): Promise<any> {
  const url = `${BASE_URL}/api/v1/posture/sessions`;
  const response = await fetch(url, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(session),
  });
  if (!response.ok) throw new Error("Failed to save posture session");
  const json = await response.json();
  return json.data;
}
