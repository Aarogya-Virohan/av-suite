'use client';

import { createContext, useContext } from 'react';
import type { Me } from '@/lib/types';

export const PRODUCT_KEY = 'psycho-social-screening';

const MeContext = createContext<Me | null>(null);

export const MeProvider = MeContext.Provider;

export function useMe(): Me {
  const me = useContext(MeContext);
  if (!me) throw new Error('useMe outside the staff layout');
  return me;
}

export function useCan(capability: string): boolean {
  return useMe().capabilities.includes(capability);
}
