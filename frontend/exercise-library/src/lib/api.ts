const API_BASE = "http://localhost:8000/api/v1";

export async function login() {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "admin@avsuite.com",
      password: "adminpassword"
    })
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  localStorage.setItem("token", data.access_token);
  return data;
}

function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
}

export async function fetchExercises(searchQuery?: string, bodyPart?: string) {
  const params = new URLSearchParams();
  if (searchQuery) params.append("search", searchQuery);
  if (bodyPart) params.append("body_part", bodyPart);
  
  const res = await fetch(`${API_BASE}/exercises?${params.toString()}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error("Failed to fetch exercises");
  const json = await res.json();
  // Map backend model to frontend model
  return json.data.map((ex: any) => ({
    id: ex.id,
    name: ex.title,
    bodyPart: ex.body_part,
    condition: ex.body_part, // backend doesn't have condition natively
    instructions: ex.description || "",
    sets: 3, // defaults since backend exercise doesn't store these
    reps: 10,
    hold: 5,
    frequency: "Daily",
    isFree: ex.is_free
  }));
}

export async function savePrescription(items: any[]) {
  // Use a hardcoded patient ID for now since patient selection isn't fully built
  const patientId = "00000000-0000-0000-0000-000000000000"; 
  const res = await fetch(`${API_BASE}/prescriptions`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      patient_id: patientId,
      status: "draft",
      items: items.map(i => ({
        exercise_id: i.exercise.id,
        sets: i.sets,
        reps: i.reps,
        hold: i.hold,
        frequency: i.frequency,
        note: i.note
      }))
    })
  });
  if (!res.ok) throw new Error("Failed to save prescription");
  const json = await res.json();
  return json.data;
}

export async function generatePdf(prescriptionId: string) {
  const res = await fetch(`${API_BASE}/prescriptions/${prescriptionId}/pdf`, {
    method: "POST",
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error("Failed to generate PDF");
  const json = await res.json();
  return json.data.pdf_url;
}
