import { create } from 'zustand';
import { UserRole } from '../types/api';
import { getStoredToken, parseJwt, clearStoredTokens } from '../lib/auth';

interface AuthState {
  token: string | null;
  userId: string | null;
  clinicId: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  setToken: (token: string, refreshToken?: string) => void;
  initializeFromStorage: () => void;
  logout: () => void;
}

interface UiState {
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (isOpen: boolean) => void;
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  userId: null,
  clinicId: null,
  role: null,
  isAuthenticated: false,
  setToken: (token: string) => {
    const claims = parseJwt(token);
    set({
      token,
      userId: claims?.sub || null,
      clinicId: claims?.clinic_id || null,
      role: claims?.role || 'admin',
      isAuthenticated: true,
    });
  },
  initializeFromStorage: () => {
    const token = getStoredToken();
    if (token) {
      const claims = parseJwt(token);
      if (claims) {
        set({
          token,
          userId: claims.sub,
          clinicId: claims.clinic_id,
          role: claims.role,
          isAuthenticated: true,
        });
        return;
      }
    }
    set({
      token: null,
      userId: null,
      clinicId: null,
      role: null,
      isAuthenticated: false,
    });
  },
  logout: () => {
    clearStoredTokens();
    set({
      token: null,
      userId: null,
      clinicId: null,
      role: null,
      isAuthenticated: false,
    });
  },
}));

export const useUiStore = create<UiState>((set) => ({
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  theme: 'light',
  setTheme: (theme) => set({ theme }),
}));
