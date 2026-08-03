import type { AuthSession, UserRole } from './auth.types';

const AUTH_TOKEN_KEY = 'aarogya_crm_access_token';
const AUTH_SESSION_KEY = 'aarogya_crm_auth_session';
const LEGACY_TOKEN_KEY = 'token';
const LEGACY_EMAIL_KEY = 'userEmail';
const CLOCK_SKEW_SECONDS = 30;

interface JwtClaims {
  sub?: unknown;
  clinic_id?: unknown;
  role?: unknown;
  exp?: unknown;
  iat?: unknown;
}

const normalizeRole = (role: unknown): UserRole | null => {
  if (typeof role !== 'string') {
    return null;
  }

  const normalizedRole = role.trim().toLowerCase();
  if (normalizedRole === 'physio') {
    return 'therapist';
  }

  if (
    normalizedRole === 'admin' ||
    normalizedRole === 'therapist' ||
    normalizedRole === 'front_desk' ||
    normalizedRole === 'patient'
  ) {
    return normalizedRole;
  }

  return null;
};

const decodeBase64Url = (value: string): string => {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');

  return globalThis.atob(padded);
};

const parseJwtClaims = (token: string): JwtClaims | null => {
  const parts = token.split('.');
  if (parts.length !== 3 || parts.some((part) => part.length === 0)) {
    return null;
  }

  try {
    return JSON.parse(decodeBase64Url(parts[1])) as JwtClaims;
  } catch {
    return null;
  }
};

export const createAuthSession = (token: string, email?: string): AuthSession | null => {
  const claims = parseJwtClaims(token);
  if (!claims) {
    return null;
  }

  const role = normalizeRole(claims.role);
  if (
    typeof claims.sub !== 'string' ||
    typeof claims.clinic_id !== 'string' ||
    typeof claims.exp !== 'number' ||
    !role
  ) {
    return null;
  }

  const expiresAt = claims.exp;
  const now = Math.floor(Date.now() / 1000);
  if (expiresAt <= now + CLOCK_SKEW_SECONDS) {
    return null;
  }

  return {
    token,
    userId: claims.sub,
    clinicId: claims.clinic_id,
    role,
    expiresAt,
    issuedAt: typeof claims.iat === 'number' ? claims.iat : undefined,
    email,
  };
};

export const clearAuthSession = () => {
  if (typeof window === 'undefined') {
    return;
  }

  window.sessionStorage.removeItem(AUTH_TOKEN_KEY);
  window.sessionStorage.removeItem(AUTH_SESSION_KEY);
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_SESSION_KEY);
  window.localStorage.removeItem(LEGACY_TOKEN_KEY);
  window.localStorage.removeItem(LEGACY_EMAIL_KEY);
};

export const saveAuthSession = (token: string, email?: string): AuthSession | null => {
  if (typeof window === 'undefined') {
    return null;
  }

  const session = createAuthSession(token, email);
  if (!session) {
    clearAuthSession();
    return null;
  }

  window.sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  window.sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(session));
  window.localStorage.removeItem(LEGACY_TOKEN_KEY);
  window.localStorage.removeItem(LEGACY_EMAIL_KEY);
  return session;
};

export const getAuthSession = (): AuthSession | null => {
  if (typeof window === 'undefined') {
    return null;
  }

  const sessionJson = window.sessionStorage.getItem(AUTH_SESSION_KEY);
  const token = window.sessionStorage.getItem(AUTH_TOKEN_KEY);
  if (sessionJson && token) {
    try {
      const savedSession = JSON.parse(sessionJson) as AuthSession;
      const session = createAuthSession(token, savedSession.email);
      if (session) {
        return session;
      }
    } catch {
      clearAuthSession();
      return null;
    }
  }

  const legacyToken = window.localStorage.getItem(LEGACY_TOKEN_KEY);
  if (legacyToken) {
    const migratedSession = saveAuthSession(
      legacyToken,
      window.localStorage.getItem(LEGACY_EMAIL_KEY) || undefined
    );
    if (migratedSession) {
      return migratedSession;
    }
  }

  clearAuthSession();
  return null;
};

export const getStoredAuthToken = (): string | null => getAuthSession()?.token ?? null;

export const isAdminRole = (role: UserRole): boolean => role === 'admin';
