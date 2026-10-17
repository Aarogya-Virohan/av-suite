import { afterEach, describe, expect, it } from 'vitest';
import { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from 'axios';
import { apiClient, apiErrorCode } from './api-client';

const originalAdapter = apiClient.defaults.adapter;

/** Makes the next request fail with the given status and body. */
function failWith(status: number, data: unknown) {
  apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
    throw new AxiosError(`Request failed with status code ${status}`, 'ERR_BAD_REQUEST', config, null, {
      status,
      statusText: '',
      headers: new AxiosHeaders(),
      config,
      data,
    });
  };
}

afterEach(() => {
  apiClient.defaults.adapter = originalAdapter;
});

describe('api-client error messages', () => {
  it('reads message and code from a structured detail object', async () => {
    failWith(400, {
      detail: { code: 'WORKSPACE_SELECTION_REQUIRED', message: 'Select a workspace to continue.', workspaces: [] },
    });
    const err = await apiClient.post('/auth/login', {}).catch((e) => e);
    expect(err.message).toBe('Select a workspace to continue.');
    expect(apiErrorCode(err)).toBe('WORKSPACE_SELECTION_REQUIRED');
  });

  it('still reads a plain string detail', async () => {
    failWith(409, { detail: 'Email already registered' });
    const err = await apiClient.post('/users', {}).catch((e) => e);
    expect(err.message).toBe('Email already registered');
  });

  it('still joins a validation array', async () => {
    failWith(422, { detail: [{ msg: "Input should be 'active', 'inactive' or 'discharged'" }] });
    const err = await apiClient.get('/patients').catch((e) => e);
    expect(err.message).toBe("Input should be 'active', 'inactive' or 'discharged'");
  });
});
