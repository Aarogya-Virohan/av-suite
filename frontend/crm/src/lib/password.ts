/**
 * bcrypt on the backend only accepts passwords up to 72 bytes (UTF-8). The
 * API answers 422 above that; checking here gives the message before submit.
 */
export const MAX_PASSWORD_BYTES = 72;

export function passwordTooLong(password: string): boolean {
  return new TextEncoder().encode(password).length > MAX_PASSWORD_BYTES;
}

export const PASSWORD_TOO_LONG_MESSAGE = 'Password is too long (max 72 English characters, fewer with other scripts or emoji)';
