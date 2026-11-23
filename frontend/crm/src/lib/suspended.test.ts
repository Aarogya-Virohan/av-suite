import { afterEach, describe, expect, it } from 'vitest';
import { clearSuspended, getSuspended, reportSuspended, suspendedLevel, SUSPENDED_DETAIL, SUSPENDED_TITLE } from './suspended';

afterEach(() => clearSuspended());

describe('suspended (U4)', () => {
  it('level: organization only when the backend says so', () => {
    expect(suspendedLevel({ level: 'organization' })).toBe('organization');
    expect(suspendedLevel({ level: 'clinic' })).toBe('clinic');
    expect(suspendedLevel(undefined)).toBe('clinic');
  });

  it('report clears the shared session keys and sets the level', () => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('token', 't');
    window.localStorage.setItem('userEmail', 'a@b.c');
    reportSuspended({ level: 'organization' });
    expect(getSuspended()).toBe('organization');
    expect(window.localStorage.getItem('token')).toBeNull();
    expect(window.localStorage.getItem('userEmail')).toBeNull();
  });

  it('exact copy', () => {
    expect(SUSPENDED_TITLE).toBe("Your clinic's access is paused. Please contact AV support.");
    expect(SUSPENDED_DETAIL).toEqual({ clinic: 'This clinic is paused.', organization: "Your organization's account is paused." });
  });
});
