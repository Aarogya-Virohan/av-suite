import type { MetaErrorDetails } from './types';

/**
 * Error codes the console reacts to. The backend sends them in
 * {data: null, meta: {error: {code, message, field}}}.
 * confirm in S2/S3: final code names of the platform routes.
 */
export const PLATFORM_ERROR_CODES = {
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  CONFLICT: 'CONFLICT',
  MFA_INVALID: 'MFA_INVALID',
  NETWORK_ERROR: 'NETWORK_ERROR',
} as const;

export class PlatformApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly field: string | null;

  constructor(status: number, details: MetaErrorDetails) {
    super(details.message);
    this.name = 'PlatformApiError';
    this.status = status;
    this.code = details.code;
    this.field = details.field ?? null;
  }
}

export function isPlatformApiError(error: unknown): error is PlatformApiError {
  return error instanceof PlatformApiError;
}

/** Human message for a failed call, safe to show in a toast. */
export function errorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (isPlatformApiError(error)) return error.message || fallback;
  return fallback;
}
