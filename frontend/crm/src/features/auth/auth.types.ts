export type UserRole = 'admin' | 'therapist' | 'front_desk' | 'patient';

export interface AuthSession {
  token: string;
  userId: string;
  clinicId: string;
  role: UserRole;
  expiresAt: number;
  issuedAt?: number;
  email?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
