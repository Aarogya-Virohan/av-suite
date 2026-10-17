/** One clinic the account belongs to, as sent by the backend on login. */
export interface WorkspaceOption {
  clinic_id: string;
  name: string;
  role: string;
}

export const ROLE_LABEL: Record<string, string> = {
  admin: 'Admin',
  therapist: 'Therapist',
  front_desk: 'Front Desk',
};

/**
 * The workspace list from a WORKSPACE_SELECTION_REQUIRED login error, or null.
 * An account that belongs to more than one clinic must say which one to open.
 */
export function workspacesFromError(err: unknown): WorkspaceOption[] | null {
  const detail = (err as { response?: { data?: { detail?: unknown } } } | null)?.response?.data?.detail as
    | { code?: string; workspaces?: unknown }
    | undefined;
  if (!detail || typeof detail !== 'object' || detail.code !== 'WORKSPACE_SELECTION_REQUIRED') return null;
  if (!Array.isArray(detail.workspaces)) return null;
  const list = detail.workspaces.filter(
    (w): w is WorkspaceOption =>
      !!w &&
      typeof w === 'object' &&
      typeof (w as WorkspaceOption).clinic_id === 'string' &&
      typeof (w as WorkspaceOption).name === 'string',
  );
  return list.length > 0 ? list : null;
}
