'use client';

import { useSyncExternalStore } from 'react';
import { getStoredToken, isTokenExpired } from './auth';

function subscribe(onChange: () => void) {
  window.addEventListener('storage', onChange);
  return () => window.removeEventListener('storage', onChange);
}

/**
 * 'valid' or 'missing' on the client, null during server render, so the
 * first client render matches the server HTML and no effect has to set
 * state to find out.
 */
export function useTokenStatus(): 'valid' | 'missing' | null {
  return useSyncExternalStore(
    subscribe,
    () => {
      const t = getStoredToken();
      return t && !isTokenExpired(t) ? 'valid' : 'missing';
    },
    () => null,
  );
}
