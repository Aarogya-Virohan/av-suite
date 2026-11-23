import { PLATFORM_ERROR_CODES, PlatformApiError } from './errors';

/*
 * Turns what the real backend sends into the PlatformApiError the screens
 * already know (same code, same wording, same `field` as the mock).
 *
 * Two shapes come back:
 *  - app errors:  { data: null, meta: { error: { code, message, details } } }
 *  - FastAPI validation (422, body / query shape):  { detail: [{ loc, msg, type }] }
 * Wording of the backend (platform_auth.py, platform_api.py) is matched in
 * lower case without a trailing full stop.
 */

interface Mapped {
  message: string;
  field?: string;
}

const KNOWN: Record<string, Mapped> = {
  'role changes via cli only': { message: 'Role changes via CLI only.', field: 'role' },
  'owner reactivation via cli only': { message: 'Owner reactivation via CLI only.' },
  'cannot deactivate the last active owner': { message: 'Cannot deactivate the last active Owner.' },
  'operators cannot deactivate themselves': { message: 'You cannot deactivate yourself.' },
  'slug already in use': { message: 'This slug is already used.', field: 'slug' },
  'reason is required': { message: 'A reason is required.', field: 'reason' },
  'valid_until must be after valid_from': { message: 'valid_until must be after valid_from.', field: 'valid_until' },
  'invalid entitlement status': { message: 'status must be one of: enabled, disabled.', field: 'status' },
  'source and target must differ': { message: 'Cannot merge an organization into itself.', field: 'source_organization_id' },
  'invalid email or password': { message: 'Email or password is incorrect.' },
  'invalid or expired challenge': { message: 'Sign-in expired. Start again.' },
  'invalid verification code': { message: 'The code is not valid.', field: 'code' },
  'mfa configuration error': { message: 'Two-step sign-in is not set up correctly for this account. Ask an Owner to reset it.' },
  'too many authentication attempts': { message: 'Too many attempts. Wait a few minutes and try again.' },
  'no supported operator change supplied': { message: 'Nothing to change.' },
  'organization not found': { message: 'Organization not found.' },
  'clinic not found': { message: 'Clinic not found.' },
  'operator not found': { message: 'Operator not found.' },
  'clinic or product not found': { message: 'Clinic or product not found.', field: 'product_key' },
};

const FALLBACK_BY_STATUS: Record<number, string> = {
  401: 'Please sign in again.',
  403: 'Your role cannot do this.',
  404: 'Not found.',
  409: 'This conflicts with the current state. Reload and try again.',
  422: 'Some values are not valid.',
  429: 'Too many attempts. Wait a few minutes and try again.',
};

function normalise(message: string): string {
  return message.trim().replace(/\.+$/, '').toLowerCase();
}

function withFullStop(message: string): string {
  const text = message.trim();
  return /[.!?]$/.test(text) ? text : `${text}.`;
}

function fieldFromLoc(loc: unknown): string | undefined {
  if (!Array.isArray(loc)) return undefined;
  const last = loc[loc.length - 1];
  return typeof last === 'string' ? last : undefined;
}

function mapValidationDetail(detail: unknown[]): Mapped {
  const first = (detail[0] ?? {}) as { loc?: unknown; msg?: unknown; type?: unknown };
  const field = fieldFromLoc(first.loc);
  const type = typeof first.type === 'string' ? first.type : '';
  const msg = typeof first.msg === 'string' ? first.msg : '';
  if (field === 'code') return { message: 'Enter the 6-digit code from your authenticator app.', field };
  if (/email/.test(type) || /email/i.test(msg)) return { message: 'Enter a valid email.', field };
  if (type === 'missing' && field) return { message: `${field} is required.`, field };
  if (/too_long|string_too_long/.test(type) && field) return { message: `${field} is too long.`, field };
  if (/too_short|string_too_short/.test(type) && field) return { message: `${field} is required.`, field };
  if (/greater_than|less_than/.test(type) && field) return { message: `${field} is out of range.`, field };
  if (/uuid/.test(type) && field) return { message: `${field} is not valid.`, field };
  if (/enum|literal/.test(type) && field) return { message: `${field} is not an allowed value.`, field };
  if (/datetime|date/.test(type) && field) return { message: `${field} is not a valid date.`, field };
  return { message: field ? `${field} is not valid.` : FALLBACK_BY_STATUS[422], field };
}

/** Build the error a screen sees from an HTTP status and the parsed response body. */
export function toPlatformApiError(status: number, body: unknown): PlatformApiError {
  const b = (body && typeof body === 'object' ? body : {}) as {
    meta?: { error?: { code?: unknown; message?: unknown } | null } | null;
    detail?: unknown;
  };

  if (status === 0) {
    return new PlatformApiError(0, { code: PLATFORM_ERROR_CODES.NETWORK_ERROR, message: 'Cannot reach the server. Check your connection and try again.' });
  }

  const envelope = b.meta?.error;
  if (envelope && typeof envelope.code === 'string') {
    const raw = typeof envelope.message === 'string' ? envelope.message : '';
    const known = KNOWN[normalise(raw)];
    // The same 403 text ("Forbidden") covers every missing permission.
    const generic403 = status === 403 && normalise(raw) === 'forbidden';
    const message = known?.message ?? (generic403 ? FALLBACK_BY_STATUS[403] : raw ? withFullStop(raw) : (FALLBACK_BY_STATUS[status] ?? 'Request failed.'));
    // "Unauthorized" on a data call means the token is gone.
    const unauthorised = status === 401 && normalise(raw) === 'unauthorized';
    return new PlatformApiError(status, {
      code: envelope.code,
      message: unauthorised ? FALLBACK_BY_STATUS[401] : message,
      field: known?.field ?? null,
    });
  }

  if (Array.isArray(b.detail) && b.detail.length > 0) {
    const mapped = mapValidationDetail(b.detail);
    return new PlatformApiError(status, { code: PLATFORM_ERROR_CODES.VALIDATION_ERROR, message: mapped.message, field: mapped.field ?? null });
  }

  const detailText = typeof b.detail === 'string' ? b.detail : '';
  if (status >= 500) {
    return new PlatformApiError(status, { code: `HTTP_${status}`, message: 'The server had a problem. Try again in a moment.' });
  }
  return new PlatformApiError(status, {
    code: `HTTP_${status}`,
    message: detailText ? withFullStop(detailText) : (FALLBACK_BY_STATUS[status] ?? 'Request failed.'),
  });
}
