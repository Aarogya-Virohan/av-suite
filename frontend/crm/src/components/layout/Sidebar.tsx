'use client';

import React from 'react';
import {
  LayoutDashboard,
  BarChart3,
  Users,
  Calendar,
  CreditCard,
  UserCheck,
  Stethoscope,
  Trash2,
  Settings,
  X
} from 'lucide-react';
import { useCRMStore } from '@/lib/store';
import { canAccessTab, formatRole } from '@/features/auth/roleAccess';
import type { UserRole } from '@/features/auth/auth.types';

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

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  isOpen: boolean;
  onClose: () => void;
  role: UserRole;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  isOpen,
  onClose,
  role
}) => {
  const branding = useCRMStore((state) => state.branding);
  const appointmentRequests = useCRMStore((state) => state.appointmentRequests);

  const pendingRequestsCount = appointmentRequests.filter((r) => r.status === 'Pending').length;

  interface NavItem {
    id: NavTab;
    label: string;
    icon: React.ReactNode;
    badge?: number;
  }

  const allNavItems: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-5 h-5" /> },
    { id: 'patients', label: 'Patients', icon: <Users className="w-5 h-5" /> },
    {
      id: 'appointments',
      label: 'Appointments',
      icon: <Calendar className="w-5 h-5" />,
      badge: pendingRequestsCount > 0 ? pendingRequestsCount : undefined
    },
    { id: 'billing', label: 'Billing', icon: <CreditCard className="w-5 h-5" /> },
    { id: 'leads', label: 'Leads', icon: <UserCheck className="w-5 h-5" /> },
    { id: 'therapists', label: 'Therapists', icon: <Stethoscope className="w-5 h-5" /> },
    { id: 'recycle', label: 'Recycle Bin', icon: <Trash2 className="w-5 h-5" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> }
  ];

  const navItems = allNavItems.filter((item) => canAccessTab(role, item.id));

  return (
    <>
      {/* Backdrop for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 left-0 h-screen w-64 bg-[var(--sidebar-bg)] text-white flex flex-col z-50 transition-transform duration-300 ease-in-out shadow-xl md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Sidebar Brand Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {branding.logoBase64 ? (
              <img
                src={branding.logoBase64}
                alt="Clinic Logo"
                className="w-8 h-8 rounded object-cover"
              />
            ) : (
              <div
                className="w-3 h-3 rounded-full animate-pulse"
                style={{ backgroundColor: branding.brandColor || '#1BB7B0' }}
              />
            )}
            <span className="font-extrabold text-lg tracking-wide truncate max-w-[160px]">
              {branding.clinicName || 'Aarogya CRM'}
            </span>
          </div>
          <button
            onClick={onClose}
            className="md:hidden text-gray-400 hover:text-white p-1 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  onClose();
                }}
                className={`w-full flex items-center justify-between px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-white/15 text-white border-l-4'
                    : 'text-white/70 hover:bg-white/5 hover:text-white'
                }`}
                style={{
                  borderLeftColor: isActive ? branding.brandColor || '#1BB7B0' : 'transparent'
                }}
              >
                <div className="flex items-center gap-3">
                  {item.icon}
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-2 py-0.5 text-xs font-bold bg-red-500 text-white rounded-full animate-pulse">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-white/10 text-xs text-white/50 text-center">
          <p className="font-semibold text-white/70">{formatRole(role)}</p>
          <p className="mt-1">AV Suite CRM v1.0 • Aarogya Virohan</p>
        </div>
      </aside>
    </>
  );
};
