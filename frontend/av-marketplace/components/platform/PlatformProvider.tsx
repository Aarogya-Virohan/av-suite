'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

import { ApiError, getPlatformContext } from '../../lib/api-client';
import type { PlatformContext } from '../../lib/api-types';

interface PlatformState {
  context: PlatformContext | null;
  loading: boolean;
  error: ApiError | null;
  refresh: () => Promise<PlatformContext | null>;
  clear: () => void;
}

const PlatformStateContext = createContext<PlatformState | null>(null);

export function PlatformProvider({ children }: { children: ReactNode }) {
  const [context, setContext] = useState<PlatformContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  async function refresh(): Promise<PlatformContext | null> {
    setLoading(true);
    try {
      const nextContext = await getPlatformContext();
      setContext(nextContext);
      setError(null);
      return nextContext;
    } catch (cause) {
      const apiError = cause instanceof ApiError
        ? cause
        : new ApiError(503, 'The platform service is unavailable. Try again shortly.');
      setContext(null);
      setError(apiError);
      return null;
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setContext(null);
    setError(null);
  }

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <PlatformStateContext.Provider value={{ context, loading, error, refresh, clear }}>
      {children}
    </PlatformStateContext.Provider>
  );
}

export function usePlatform(): PlatformState {
  const value = useContext(PlatformStateContext);
  if (!value) throw new Error('usePlatform must be used within PlatformProvider.');
  return value;
}