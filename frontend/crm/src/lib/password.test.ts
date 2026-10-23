import { describe, expect, it } from 'vitest';
import { passwordTooLong } from './password';

describe('passwordTooLong', () => {
  it('allows exactly 72 bytes and rejects 73', () => {
    expect(passwordTooLong('a'.repeat(72))).toBe(false);
    expect(passwordTooLong('a'.repeat(73))).toBe(true);
  });
  it('counts UTF-8 bytes, not characters', () => {
    expect(passwordTooLong('क'.repeat(24))).toBe(false); // 72 bytes
    expect(passwordTooLong('क'.repeat(25))).toBe(true); // 75 bytes
  });
});
