import { create } from 'zustand';
import { UserRole } from '../types/api';
import { getStoredToken, parseJwt, clearStoredTokens } from '../lib/auth';
import { apiClient } from '../lib/api-client';

export interface ClinicBranding {
  id: string;
  name: string;
  /** Public booking slug (from /auth/me). Older backends do not send it. */
  slug?: string | null;
  branding_logo_url: string | null;
  branding_color: string | null;
  /* Clinic profile for invoice headers (D-026). Older backends do not send them. */
  address_line?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
  phone?: string | null;
  email?: string | null;
  registration_number?: string | null;
  gstin?: string | null;
  authorised_person?: string | null;
}

interface AuthState {
  token: string | null;
  userId: string | null;
  clinicId: string | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  capabilities: Record<string, string>;
  clinic: ClinicBranding | null;
  setToken: (token: string, refreshToken?: string) => void;
  initializeFromStorage: () => void;
  fetchMe: () => Promise<void>;
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
  capabilities: {},
  clinic: null,
  setToken: (token: string) => {
    const claims = parseJwt(token);
    set({
      token,
      userId: claims?.sub || null,
      clinicId: claims?.clinic_id || null,
      role: claims?.role ?? null,
      isAuthenticated: true,
    });
    useAuthStore.getState().fetchMe();
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
        useAuthStore.getState().fetchMe();
        return;
      }
    }
    set({
      token: null,
      userId: null,
      clinicId: null,
      role: null,
      capabilities: {},
      clinic: null,
      isAuthenticated: false,
    });
  },
  fetchMe: async () => {
    try {
      const res = await apiClient.get('/auth/me');
      const data = res.data?.data || res.data;
      if (data) {
        set({
          userId: data.user?.id || null,
          clinicId: data.user?.clinic_id || null,
          role: data.user?.role || null,
          clinic: data.clinic || null,
          capabilities: data.capabilities || {},
          isAuthenticated: true,
        });
        if (data.clinic?.branding_color && typeof document !== 'undefined') {
          document.documentElement.style.setProperty('--brand-navy', data.clinic.branding_color);
        }
      }
    } catch (e) {
      console.error('Failed to fetch user permissions and clinic info', e);
    }
  },
  logout: () => {
    clearStoredTokens();
    set({
      token: null,
      userId: null,
      clinicId: null,
      role: null,
      capabilities: {},
      clinic: null,
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
