import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UserPermissionsSlideOver } from './components/UserPermissionsSlideOver';
import { apiClient } from '../../lib/api-client';
import type { User } from '../../types/api';

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const user = {
  id: 'u-1',
  first_name: 'Asha',
  last_name: 'Rao',
  role: 'therapist',
} as unknown as User;

const SCREENING_KEY = 'screening.view';

function renderSlideOver() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <UserPermissionsSlideOver isOpen onClose={() => {}} user={user} />
    </QueryClientProvider>,
  );
}

describe('UserPermissionsSlideOver', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    cleanup();
  });

  it('shows a loading state and no Save button while permissions load', () => {
    vi.spyOn(apiClient, 'get').mockReturnValue(new Promise(() => {}));
    renderSlideOver();
    expect(screen.getByRole('status', { name: 'Loading permissions' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /save overrides/i })).toBeNull();
  });

  it('shows an error with retry and never offers Save when the GET fails', async () => {
    const get = vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('Network Error'));
    const put = vi.spyOn(apiClient, 'put');
    renderSlideOver();

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText(/could not load this user's saved permissions/i)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /save overrides/i })).toBeNull();
    expect(screen.queryAllByRole('combobox')).toHaveLength(0);

    // Retry succeeds: the form appears with the saved values.
    get.mockResolvedValue({ data: { data: [{ capability_key: 'patients.view', scope: 'all' }] } });
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    expect(await screen.findByRole('button', { name: /save overrides/i })).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(get).toHaveBeenCalledTimes(2);
    expect(put).not.toHaveBeenCalled();
  });

  it('treats an unexpected response shape as an error, not as no overrides', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: {} });
    renderSlideOver();
    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /save overrides/i })).toBeNull();
  });

  it('keeps saved keys the form does not list when saving', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: {
        data: [
          { capability_key: SCREENING_KEY, scope: 'own' },
          { capability_key: 'patients.view', scope: 'all' },
        ],
      },
    });
    const put = vi.spyOn(apiClient, 'put').mockResolvedValue({ data: { data: [] } });
    renderSlideOver();

    fireEvent.click(await screen.findByRole('button', { name: /save overrides/i }));
    await waitFor(() => expect(put).toHaveBeenCalledTimes(1));

    const [url, payload] = put.mock.calls[0] as [string, { capability_key: string; scope: string }[]];
    expect(url).toBe('/users/u-1/permissions');
    expect(payload).toContainEqual({ capability_key: SCREENING_KEY, scope: 'own' });
    expect(payload).toContainEqual({ capability_key: 'patients.view', scope: 'all' });
  });
});
