import { describe, expect, it } from 'vitest';
import { toPlatformApiError } from './http-errors';

const envelope = (code: string, message: string) => ({ data: null, meta: { error: { code, message, details: {} } } });

describe('toPlatformApiError: backend answers become the messages the screens already show', () => {
  it('operator rules (S2): role change 403, last Owner 409, self 422, Owner reactivation 403', () => {
    expect(toPlatformApiError(403, envelope('FORBIDDEN', 'Role changes via CLI only'))).toMatchObject({
      status: 403, code: 'FORBIDDEN', message: 'Role changes via CLI only.', field: 'role',
    });
    expect(toPlatformApiError(409, envelope('CONFLICT', 'Cannot deactivate the last active Owner'))).toMatchObject({
      status: 409, code: 'CONFLICT', message: 'Cannot deactivate the last active Owner.',
    });
    expect(toPlatformApiError(422, envelope('VALIDATION_ERROR', 'Operators cannot deactivate themselves'))).toMatchObject({
      status: 422, code: 'VALIDATION_ERROR', message: 'You cannot deactivate yourself.',
    });
    expect(toPlatformApiError(403, envelope('FORBIDDEN', 'Owner reactivation via CLI only'))).toMatchObject({
      status: 403, message: 'Owner reactivation via CLI only.',
    });
  });

  it('duplicate slug 409 points at the slug field; missing reason 422 at the reason field', () => {
    expect(toPlatformApiError(409, envelope('CONFLICT', 'Slug already in use'))).toMatchObject({
      status: 409, message: 'This slug is already used.', field: 'slug',
    });
    expect(toPlatformApiError(422, envelope('VALIDATION_ERROR', 'Reason is required'))).toMatchObject({
      status: 422, message: 'A reason is required.', field: 'reason',
    });
    expect(toPlatformApiError(422, envelope('VALIDATION_ERROR', 'valid_until must be after valid_from'))).toMatchObject({ field: 'valid_until' });
  });

  it('a generic 403 means the role cannot do this', () => {
    expect(toPlatformApiError(403, envelope('FORBIDDEN', 'Forbidden'))).toMatchObject({ status: 403, message: 'Your role cannot do this.' });
  });

  it('sign-in failures keep their code', () => {
    expect(toPlatformApiError(401, envelope('UNAUTHORIZED', 'Invalid email or password'))).toMatchObject({
      status: 401, code: 'UNAUTHORIZED', message: 'Email or password is incorrect.',
    });
    expect(toPlatformApiError(401, envelope('MFA_INVALID', 'Invalid verification code'))).toMatchObject({
      status: 401, code: 'MFA_INVALID', message: 'The code is not valid.', field: 'code',
    });
    expect(toPlatformApiError(401, envelope('UNAUTHORIZED', 'Invalid or expired challenge'))).toMatchObject({ message: 'Sign-in expired. Start again.' });
    expect(toPlatformApiError(401, envelope('UNAUTHORIZED', 'Unauthorized'))).toMatchObject({ message: 'Please sign in again.' });
    expect(toPlatformApiError(429, envelope('RATE_LIMITED', 'Too many authentication attempts'))).toMatchObject({
      status: 429, code: 'RATE_LIMITED', message: 'Too many attempts. Wait a few minutes and try again.',
    });
  });

  it('FastAPI validation (detail array) becomes a 422 with the field', () => {
    const error = toPlatformApiError(422, { detail: [{ loc: ['body', 'email'], msg: 'value is not a valid email address', type: 'value_error' }] });
    expect(error).toMatchObject({ status: 422, code: 'VALIDATION_ERROR', message: 'Enter a valid email.', field: 'email' });
    expect(toPlatformApiError(422, { detail: [{ loc: ['body', 'code'], msg: 'String should match pattern', type: 'string_pattern_mismatch' }] })).toMatchObject({ field: 'code' });
    expect(toPlatformApiError(422, { detail: [{ loc: ['query', 'page_size'], msg: 'Input should be less than or equal to 100', type: 'less_than_equal' }] })).toMatchObject({ field: 'page_size', message: 'page_size is out of range.' });
  });

  it('network failure, server failure and unknown bodies never leak raw text', () => {
    expect(toPlatformApiError(0, undefined)).toMatchObject({ status: 0, code: 'NETWORK_ERROR' });
    expect(toPlatformApiError(500, '<html>boom</html>')).toMatchObject({ status: 500, code: 'HTTP_500', message: 'The server had a problem. Try again in a moment.' });
    expect(toPlatformApiError(404, { detail: 'Not Found' })).toMatchObject({ status: 404, message: 'Not Found.' });
  });

  it('keeps unknown backend wording (with a full stop) so nothing is hidden', () => {
    expect(toPlatformApiError(404, envelope('NOT_FOUND', 'Something new'))).toMatchObject({ code: 'NOT_FOUND', message: 'Something new.', field: null });
  });
});
