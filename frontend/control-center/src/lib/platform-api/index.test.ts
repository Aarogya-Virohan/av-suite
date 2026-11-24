import { describe, expect, it } from 'vitest';
import { resolveApiBaseUrl, resolveApiMode } from './index';

describe('resolveApiMode: mock data only when asked for in a production build', () => {
  it('production without a value uses the real API', () => {
    expect(resolveApiMode(undefined, 'production')).toBe('http');
    expect(resolveApiMode('', 'production')).toBe('http');
    expect(resolveApiMode('Mock', 'production')).toBe('http');
    expect(resolveApiMode('mok', 'production')).toBe('http');
  });
  it('production with mode=mock is the one way to get mock data', () => {
    expect(resolveApiMode('mock', 'production')).toBe('mock');
  });
  it('development and tests default to mock, http when asked', () => {
    expect(resolveApiMode(undefined, 'development')).toBe('mock');
    expect(resolveApiMode(undefined, 'test')).toBe('mock');
    expect(resolveApiMode('http', 'development')).toBe('http');
  });
});

describe('resolveApiBaseUrl: a production build never guesses a host', () => {
  it('uses a valid URL and trims trailing slashes', () => {
    expect(resolveApiBaseUrl('https://api.example.com/', 'production')).toBe('https://api.example.com');
  });
  it('production without a valid URL is null (calls fail with a clear message)', () => {
    expect(resolveApiBaseUrl(undefined, 'production')).toBeNull();
    expect(resolveApiBaseUrl('', 'production')).toBeNull();
    expect(resolveApiBaseUrl('api.example.com', 'production')).toBeNull();
    expect(resolveApiBaseUrl('javascript:alert(1)', 'production')).toBeNull();
  });
  it('development falls back to the local backend', () => {
    expect(resolveApiBaseUrl(undefined, 'development')).toBe('http://localhost:8000');
  });
});
