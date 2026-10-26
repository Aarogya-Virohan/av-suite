import { Exercise, ExercisePhoto, Patient, PhotoAngle, SavedPrescription } from "@/types/exercise";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API = `${BASE_URL}/api/v1`;

const TOKEN_KEY = "token";
const EMAIL_KEY = "userEmail";

// --------------------------------------------------------------- session

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setSession(token: string, email: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(EMAIL_KEY, email);
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
  } catch {
    // storage blocked: nothing to clear
  }
}

// --------------------------------------------------------------- errors

export interface WorkspaceOption {
  clinic_id: string;
  name: string;
  role?: string;
}

/**
 * Error from the API with the backend's message, never "[object Object]".
 * The backend sends either detail: "text" (FastAPI HTTPException),
 * detail: {code, message, ...} (structured errors such as
 * WORKSPACE_SELECTION_REQUIRED), detail: [...] (validation) or
 * meta.error.message (the envelope).
 */
export class ApiError extends Error {
  status: number;
  code?: string;
  workspaces?: WorkspaceOption[];

  constructor(message: string, status: number, code?: string, workspaces?: WorkspaceOption[]) {
    super(message);
    this.status = status;
    this.code = code;
    this.workspaces = workspaces;
  }
}

function friendlyStatus(status: number): string {
  if (status === 401) return "Your session has ended. Please sign in again.";
  if (status === 403) return "You do not have access to this.";
  if (status === 404) return "Not found.";
  if (status >= 500) return "The server ran into a problem. Please try again.";
  return "Something went wrong. Please try again.";
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // not JSON
  }
  const b = body as {
    detail?: unknown;
    message?: unknown;
    meta?: { error?: { message?: unknown; code?: unknown } };
  } | null;
  const detail = b?.detail;

  let message: string | undefined;
  let code: string | undefined;
  let workspaces: WorkspaceOption[] | undefined;

  if (typeof detail === "string") {
    message = detail;
  } else if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: unknown } | undefined;
    if (typeof first?.msg === "string") message = first.msg.replace(/^Value error, /, "");
  } else if (detail && typeof detail === "object") {
    const d = detail as { message?: unknown; code?: unknown; workspaces?: unknown };
    if (typeof d.message === "string") message = d.message;
    if (typeof d.code === "string") code = d.code;
    if (Array.isArray(d.workspaces)) {
      workspaces = d.workspaces.filter(
        (w): w is WorkspaceOption =>
          !!w &&
          typeof (w as WorkspaceOption).clinic_id === "string" &&
          typeof (w as WorkspaceOption).name === "string"
      );
    }
  }
  if (!message && typeof b?.meta?.error?.message === "string") message = b.meta.error.message;
  if (!code && typeof b?.meta?.error?.code === "string") code = b.meta.error.code;
  if (!message && typeof b?.message === "string") message = b.message;

  return new ApiError(message || friendlyStatus(response.status), response.status, code, workspaces);
}

function networkError(): ApiError {
  return new ApiError(
    "Could not reach the server. Check your internet connection and try again.",
    0,
    "NETWORK"
  );
}

// --------------------------------------------------------------- request

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  // FormData sets its own multipart Content-Type with the boundary.
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API}${path}`, { ...init, headers });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw networkError();
  }
  if (response.ok) return response;

  const error = await toApiError(response);
  // Expired or revoked token: back to login instead of a broken page.
  if (response.status === 401 && token && typeof window !== "undefined") {
    clearSession();
    window.location.assign("/login?expired=1");
  }
  throw error;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await request(path, init);
  const body = await response.json();
  return body.data as T;
}

// --------------------------------------------------------------- auth

export async function login(email: string, password: string, clinicId?: string): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(clinicId ? { email, password, clinic_id: clinicId } : { email, password }),
    });
  } catch {
    throw networkError();
  }
  if (!response.ok) {
    const error = await toApiError(response);
    if (response.status === 401) error.message = "Incorrect email or password.";
    throw error;
  }
  const body = await response.json();
  const token = body?.data?.access_token;
  if (typeof token !== "string" || !token) {
    throw new ApiError("The server did not return a session. Please try again.", response.status);
  }
  return token;
}

export interface Me {
  user: { first_name?: string | null; last_name?: string | null; email: string };
  clinic: { name: string } | null;
  /** Capability key to scope ("none", "own" or "all"). */
  capabilities?: Record<string, string>;
}

export function can(me: Me | null, capability: string): boolean {
  const scope = me?.capabilities?.[capability];
  return !!scope && scope !== "none";
}

export function fetchMe(): Promise<Me> {
  return json<Me>("/auth/me");
}

// --------------------------------------------------------------- exercises

// Map backend exercise fields to the frontend model.
export function mapBackendExerciseToFrontend(be: Record<string, unknown>): Exercise {
  return {
    id: String(be.id),
    name: String(be.title ?? ""),
    bodyPart: ((be.body_part as string) || "").trim() || "Other",
    condition: (be.condition as string) || "General Recovery",
    instructions: (be.description as string) || "",
    sets: (be.sets as number) || 3,
    reps: (be.reps as number) || 10,
    hold: (be.hold as number) || 0,
    frequency: (be.frequency as string) || "Daily",
    isFree: Boolean(be.is_free),
    // The API splits the stored media link into a picture and a demo video
    // (EL-D-003); a video link is never used as an image source.
    videoUrl: (be.demo_video_url as string) || "",
    imageUrl: (be.image_url as string) || "",
    photos: mapPhotos(be.photos),
  };
}

function mapPhotos(raw: unknown): ExercisePhoto[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter(
      (p): p is { angle: PhotoAngle; updated_at: string } =>
        !!p && (p.angle === "front" || p.angle === "side") && typeof p.updated_at === "string"
    )
    .map((p) => ({ angle: p.angle, updatedAt: p.updated_at }));
}

// --------------------------------------------------------------- exercise photos

/** The photo as a blob URL. The endpoint needs the login token, so a plain
 * <img src> cannot load it. The caller revokes the URL when done. */
export async function fetchExercisePhoto(exerciseId: string, angle: PhotoAngle): Promise<string> {
  const response = await request(`/exercises/${encodeURIComponent(exerciseId)}/photos/${angle}`);
  return URL.createObjectURL(await response.blob());
}

export async function uploadExercisePhoto(
  exerciseId: string,
  angle: PhotoAngle,
  file: File
): Promise<ExercisePhoto> {
  const form = new FormData();
  form.append("file", file);
  const data = await json<{ angle: PhotoAngle; updated_at: string }>(
    `/exercises/${encodeURIComponent(exerciseId)}/photos/${angle}`,
    { method: "PUT", body: form }
  );
  return { angle: data.angle, updatedAt: data.updated_at };
}

export async function deleteExercisePhoto(exerciseId: string, angle: PhotoAngle): Promise<void> {
  await request(`/exercises/${encodeURIComponent(exerciseId)}/photos/${angle}`, { method: "DELETE" });
}

export interface ExercisePage {
  items: Exercise[];
  total: number;
}

/**
 * One page of exercises, ordered head to toe by the backend. The library
 * loads pages as the user scrolls, so it works for thousands of exercises.
 */
export async function fetchExercises(
  opts: { search?: string; bodyParts?: string[]; page?: number; pageSize?: number },
  signal?: AbortSignal
): Promise<ExercisePage> {
  const params = new URLSearchParams({
    page: String(opts.page ?? 1),
    page_size: String(opts.pageSize ?? 30),
  });
  if (opts.search) params.set("search", opts.search);
  if (opts.bodyParts?.length) params.set("body_part", opts.bodyParts.join(","));
  const response = await request(`/exercises?${params}`, { signal });
  const body = await response.json();
  const items = ((body.data as Record<string, unknown>[]) || []).map(mapBackendExerciseToFrontend);
  const total = typeof body.meta?.total === "number" ? body.meta.total : items.length;
  return { items, total };
}

export interface BodyPartCount {
  body_part: string;
  count: number;
}

/** Every body part the clinic can see, head to toe, with counts. */
export async function fetchBodyParts(): Promise<BodyPartCount[]> {
  return (await json<BodyPartCount[]>("/exercises/body-parts")) || [];
}

// --------------------------------------------------------------- patients

export async function fetchPatients(): Promise<Patient[]> {
  return (await json<Patient[]>("/patients?page_size=100")) || [];
}

export function createPatient(patient: {
  first_name: string;
  last_name: string;
  date_of_birth?: string;
  phone?: string;
}): Promise<Patient> {
  return json<Patient>("/patients", { method: "POST", body: JSON.stringify(patient) });
}

// --------------------------------------------------------------- prescriptions

export interface PrescriptionItemPayload {
  exercise_id: string;
  sets: number;
  reps: number;
  hold: number;
  frequency: string;
  note?: string;
}

export async function fetchPrescriptions(patientId: string): Promise<SavedPrescription[]> {
  const params = new URLSearchParams({ patient_id: patientId, page_size: "50" });
  const data = (await json<SavedPrescription[]>(`/prescriptions?${params}`)) || [];
  return [...data].sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export function createPrescription(prescription: {
  patient_id: string;
  physio_notes?: string;
  status?: string;
  items: PrescriptionItemPayload[];
}): Promise<SavedPrescription> {
  return json<SavedPrescription>("/prescriptions", {
    method: "POST",
    body: JSON.stringify(prescription),
  });
}

export function updatePrescription(
  id: string,
  patch: { physio_notes?: string; status?: string; items?: PrescriptionItemPayload[] }
): Promise<SavedPrescription> {
  return json<SavedPrescription>(`/prescriptions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export interface NoteSuggestions {
  notes: string[];
  guidance: string[];
}

/** Phrases this clinic already wrote, most used first. */
export async function fetchNoteSuggestions(): Promise<NoteSuggestions> {
  const data = await json<NoteSuggestions>("/prescriptions/note-suggestions");
  return { notes: data?.notes ?? [], guidance: data?.guidance ?? [] };
}

function filenameFrom(disposition: string | null): string | null {
  const m = disposition?.match(/filename="?([^";]+)"?/i);
  return m ? m[1] : null;
}

/**
 * Build the PDF on the server, then fetch it with the session (the download
 * endpoint needs auth, so a plain link cannot be used).
 */
export async function downloadPrescriptionPDF(id: string): Promise<{ blob: Blob; filename: string }> {
  const meta = await json<{ filename?: string }>(`/prescriptions/${id}/pdf`, { method: "POST" });
  const response = await request(`/prescriptions/${id}/pdf/download`);
  const blob = await response.blob();
  const filename =
    filenameFrom(response.headers.get("Content-Disposition")) || meta?.filename || "Prescription.pdf";
  return { blob, filename };
}

/** Save a blob under a file name (direct download, no new tab). */
export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
