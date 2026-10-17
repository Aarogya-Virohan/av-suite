import { describe, expect, it } from 'vitest';
import { workspacesFromError } from './workspaces';

const loginError = (detail: unknown) => ({ response: { status: 400, data: { detail } } });

describe('workspacesFromError', () => {
  it('returns the workspaces of a WORKSPACE_SELECTION_REQUIRED error', () => {
    const list = workspacesFromError(
      loginError({
        code: 'WORKSPACE_SELECTION_REQUIRED',
        message: 'Select a workspace to continue.',
        workspaces: [
          { clinic_id: 'a', name: 'Alpha Physio', role: 'admin' },
          { clinic_id: 'b', name: 'Beta Physio', role: 'therapist' },
        ],
      }),
    );
    expect(list).toEqual([
      { clinic_id: 'a', name: 'Alpha Physio', role: 'admin' },
      { clinic_id: 'b', name: 'Beta Physio', role: 'therapist' },
    ]);
  });

  it('ignores other errors', () => {
    expect(workspacesFromError(loginError('Incorrect email or password'))).toBeNull();
    expect(workspacesFromError(loginError({ code: 'SOMETHING_ELSE', workspaces: [] }))).toBeNull();
    expect(workspacesFromError(new Error('Network Error'))).toBeNull();
    expect(workspacesFromError(null)).toBeNull();
  });

  it('drops malformed entries and returns null when none are usable', () => {
    expect(
      workspacesFromError(loginError({ code: 'WORKSPACE_SELECTION_REQUIRED', workspaces: [{ name: 'No id' }, null] })),
    ).toBeNull();
    expect(
      workspacesFromError(
        loginError({
          code: 'WORKSPACE_SELECTION_REQUIRED',
          workspaces: [{ name: 'No id' }, { clinic_id: 'c', name: 'Gamma', role: 'front_desk' }],
        }),
      ),
    ).toEqual([{ clinic_id: 'c', name: 'Gamma', role: 'front_desk' }]);
  });
});
