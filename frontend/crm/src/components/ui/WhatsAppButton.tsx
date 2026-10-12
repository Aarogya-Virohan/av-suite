'use client';

import React from 'react';
import { MessageSquare } from 'lucide-react';
import { useAuthStore } from '../../store';
import { useClinicSettings } from '../../features/settings/api';
import { hasCapability } from '../../config/permissions';

interface WhatsAppButtonProps {
  phone?: string | null;
  name: string;
  message?: string;
  className?: string;
}

export function openWhatsApp(
  phone: string | null | undefined,
  name: string,
  message?: string,
  clinicName?: string | null,
) {
  if (!phone) return;
  const cleanPhone = phone.replace(/\D/g, '');
  const formattedPhone = cleanPhone.startsWith('91') ? cleanPhone : `91${cleanPhone}`;
  // Neutral greeting from the user's own clinic. It used to say "reminder for
  // your appointment with Aarogya Virohan Clinic" for every clinic, even where
  // no appointment existed. The text opens in WhatsApp for staff to edit.
  const defaultText = message || (clinicName ? `Hi ${name}, greetings from ${clinicName}.` : `Hi ${name},`);
  const url = `https://wa.me/${formattedPhone}?text=${encodeURIComponent(defaultText)}`;
  window.open(url, '_blank');
}

export function WhatsAppButton({ phone, name, message, className = '' }: WhatsAppButtonProps) {
  const authClinic = useAuthStore((s) => s.clinic);
  const { data: clinicSettings } = useClinicSettings(!authClinic?.name && hasCapability('settings.view'));
  const clinicName = authClinic?.name || clinicSettings?.name || null;
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        openWhatsApp(phone, name, message, clinicName);
      }}
      className={`px-2 py-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors shadow-xs ${className}`}
      title={`Send WhatsApp message to ${name}`}
    >
      <MessageSquare className="w-3.5 h-3.5" />
      <span>WA</span>
    </button>
  );
}
