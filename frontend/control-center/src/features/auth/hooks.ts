'use client';

import { useMutation } from '@tanstack/react-query';
import { platformApi } from '@/lib/platform-api';
import type { LoginRequest, MfaRequest } from '@/lib/platform-api/types';
import { useSession } from '@/store/session';

export function useLogin() {
  return useMutation({
    mutationFn: async (body: LoginRequest) => (await platformApi().login(body)).data,
  });
}

export function useVerifyMfa() {
  const signIn = useSession((s) => s.signIn);
  return useMutation({
    mutationFn: async (body: MfaRequest) => (await platformApi().verifyMfa(body)).data,
    onSuccess: (result) => signIn(result.access_token, result.operator, result.expires_in),
  });
}
