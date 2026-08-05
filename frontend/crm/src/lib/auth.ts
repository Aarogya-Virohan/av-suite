import { UserRole } from '../types/api';

const TOKEN_KEY = 'av_crm_access_token';
const REFRESH_TOKEN_KEY = 'av_crm_refresh_token';

export interface JwtPayload {
  sub: string;        // user_id
  clinic_id: string;  // clinic_id
  role: UserRole;     // role
  exp?: number;
}

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string, refreshToken?: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function clearStoredTokens(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function parseJwt(token: string): JwtPayload | null {
  try {
    const base64Url = token.split('.')[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const decoded = JSON.parse(jsonPayload) as JwtPayload;

    // Hard rule validation: role must never be 'physio'
    if ((decoded.role as string) === 'physio') {
      decoded.role = 'therapist';
    }

    return decoded;
  } catch (e) {
    console.error('Failed to parse JWT', e);
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = parseJwt(token);
  if (!payload || !payload.exp) return true;
  const currentTime = Math.floor(Date.now() / 1000);
  return payload.exp < currentTime;
}
