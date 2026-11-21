import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { apiClient } from '../../lib/api-client';
import { UserToolsSlideOver } from './components/UserToolsSlideOver';

vi.mock('../../lib/api-client', () => ({ apiClient: { get: vi.fn(), put: vi.fn() }, apiErrorCode: vi.fn() }));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }));

const get = vi.mocked(apiClient.get);
const put = vi.mocked(apiClient.put);

const admin = { id: 'u-admin', first_name: 'Neha', last_name: 'Kapoor', email: 'a@x.in', role: 'admin', is_active: true } as any;
const toolsResponse = (psycho: boolean) => ({
  data: {
    data: {
      user_id: 'u-admin',
      role: 'admin',
      tools: { 'psycho-social-screening': psycho, 'exercise-library': true, 'posture-tool': true },
      available: { 'psycho-social-screening': true, 'exercise-library': true, 'posture-tool': true },
      labels: {},
    },
  },
});

function renderPanel(onClose = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  render(
    <QueryClientProvider client={qc}>
      <UserToolsSlideOver isOpen onClose={onClose} user={admin} />
    </QueryClientProvider>,
  );
  return onClose;
}

describe('UserToolsSlideOver on an admin row (Onkar 21 Nov: show, never pre-block)', () => {
  beforeEach(() => {
    get.mockResolvedValue(toolsResponse(false) as any);
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('lets an admin tick Psychosocial for themselves (solo clinic: server says yes)', async () => {
    put.mockResolvedValue(toolsResponse(true) as any);
    const onClose = renderPanel();
    const box = await screen.findByLabelText(/Psychosocial/);
    expect((box as HTMLInputElement).disabled).toBe(false);
    fireEvent.click(box);
    fireEvent.click(screen.getByRole('button', { name: 'Save Tool Access' }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(put).toHaveBeenCalledWith('/users/u-admin/tools', {
      tools: ['exercise-library', 'posture-tool', 'psycho-social-screening'],
    });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it("shows the server's refusal message and stays open (multi-staff clinic: 403)", async () => {
    put.mockRejectedValue(Object.assign(new Error('An admin cannot give Psychosocial to themselves in a clinic with other staff.'), { response: { status: 403 } }));
    const onClose = renderPanel();
    fireEvent.click(await screen.findByLabelText(/Psychosocial/));
    fireEvent.click(screen.getByRole('button', { name: 'Save Tool Access' }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Not saved: An admin cannot give Psychosocial to themselves');
    expect(onClose).not.toHaveBeenCalled();
  });
});
