// Same storage key and JWT handling as the CRM and Exercise Library, so a
// staff member signs in the same way in every AV Suite app.
const TOKEN_KEY = 'token';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage blocked: the session lasts for this page only */
  }
}

export function clearStoredToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* nothing to clear */
  }
}

export function isTokenExpired(token: string): boolean {
  try {
    const part = token.split('.')[1];
    if (!part) return true;
    const json = JSON.parse(atob(part.replace(/-/g, '+').replace(/_/g, '/'))) as { exp?: number };
    if (!json.exp) return true;
    return json.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
}
