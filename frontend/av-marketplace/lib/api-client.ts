import type {
  ActiveProduct,
  ApiEnvelope,
  InstalledProduct,
  MarketplaceEntitlement,
  MarketplaceProduct,
  PlatformContext,
} from './api-types';

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function errorMessage(payload: unknown, status: number): string {
  if (isRecord(payload)) {
    const meta = payload.meta;
    if (isRecord(meta) && isRecord(meta.error)) {
      const message = meta.error.message;
      if (typeof message === 'string') return message;
    }
    const detail = payload.detail;
    if (typeof detail === 'string') return detail;
  }

  if (status === 401) return 'Your session has expired. Sign in again.';
  if (status === 403) return 'You do not have access to this product.';
  if (status === 404) return 'The requested product could not be found.';
  if (status >= 500) return 'The platform service is unavailable. Try again shortly.';
  return 'The request could not be completed. Please try again.';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/platform/${path}`, {
      ...init,
      cache: 'no-store',
      headers: {
        Accept: 'application/json',
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(503, 'Cannot reach the platform service. Check your connection.');
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(payload, response.status));
  }
  if (!isRecord(payload) || !('data' in payload)) {
    throw new ApiError(502, 'The platform returned an unexpected response.');
  }

  return payload.data as T;
}

export async function getPlatformContext(): Promise<PlatformContext> {
  return request<PlatformContext>('me');
}

export async function getMarketplaceProducts(): Promise<MarketplaceProduct[]> {
  return request<MarketplaceProduct[]>('marketplace/products');
}

export async function getInstalledProducts(): Promise<InstalledProduct[]> {
  return request<InstalledProduct[]>('marketplace/installed');
}

export async function installProduct(productKey: string): Promise<MarketplaceEntitlement> {
  return request<MarketplaceEntitlement>(
    `marketplace/products/${encodeURIComponent(productKey)}/install`,
    { method: 'POST' },
  );
}

export async function enableProduct(productKey: string): Promise<MarketplaceEntitlement> {
  return request<MarketplaceEntitlement>(
    `marketplace/products/${encodeURIComponent(productKey)}/enable`,
    { method: 'POST' },
  );
}

export async function disableProduct(productKey: string): Promise<MarketplaceEntitlement> {
  return request<MarketplaceEntitlement>(
    `marketplace/products/${encodeURIComponent(productKey)}/disable`,
    { method: 'POST' },
  );
}

export async function createSession(email: string, password: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch('/api/session/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email, password }),
      cache: 'no-store',
    });
  } catch {
    throw new ApiError(503, 'Cannot reach the platform service. Check your connection.');
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(payload, response.status));
  }
}

export async function endSession(): Promise<void> {
  const response = await fetch('/api/session/logout', {
    method: 'POST',
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new ApiError(response.status, 'Could not end the session. Please try again.');
  }
}