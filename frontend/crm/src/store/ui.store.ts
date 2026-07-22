import { create } from 'zustand';

export type NavTab =
  | 'dashboard'
  | 'analytics'
  | 'patients'
  | 'appointments'
  | 'billing'
  | 'leads'
  | 'therapists'
  | 'recycle'
  | 'settings';

interface UIState {
  sidebarOpen: boolean;
  activeTab: NavTab;
  theme: 'light' | 'dark';
  selectedPatientId: string | null;
  
  // Dialog States
  patientModalOpen: boolean;
  apptModalOpen: boolean;
  invoiceModalOpen: boolean;
  paymentModalOpen: boolean;

  setSidebarOpen: (open: boolean) => void;
  setActiveTab: (tab: NavTab) => void;
  toggleTheme: () => void;
  setSelectedPatientId: (id: string | null) => void;
  setPatientModalOpen: (open: boolean) => void;
  setApptModalOpen: (open: boolean) => void;
  setInvoiceModalOpen: (open: boolean) => void;
  setPaymentModalOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  activeTab: 'dashboard',
  theme: 'light',
  selectedPatientId: null,

  patientModalOpen: false,
  apptModalOpen: false,
  invoiceModalOpen: false,
  paymentModalOpen: false,

  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleTheme: () => set((state) => {
    const nextTheme = state.theme === 'light' ? 'dark' : 'light';
    if (typeof window !== 'undefined') {
      if (nextTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('aarogya_theme', 'dark');
      } else {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('aarogya_theme', 'light');
      }
    }
    return { theme: nextTheme };
  }),
  setSelectedPatientId: (id) => set({ selectedPatientId: id }),
  setPatientModalOpen: (open) => set({ patientModalOpen: open }),
  setApptModalOpen: (open) => set({ apptModalOpen: open }),
  setInvoiceModalOpen: (open) => set({ invoiceModalOpen: open }),
  setPaymentModalOpen: (open) => set({ paymentModalOpen: open }),
}));
