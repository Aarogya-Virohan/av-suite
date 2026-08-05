'use client';

import React from 'react';
import { MessageSquare } from 'lucide-react';

interface WhatsAppButtonProps {
  phone: string;
  name: string;
  message?: string;
  className?: string;
}

export function openWhatsApp(phone: string, name: string, message?: string) {
  if (!phone) return;
  const cleanPhone = phone.replace(/\D/g, '');
  const formattedPhone = cleanPhone.startsWith('91') ? cleanPhone : `91${cleanPhone}`;
  const defaultText = message || `Hi ${name}, reminder for your appointment with Aarogya Virohan Clinic.`;
  const url = `https://wa.me/${formattedPhone}?text=${encodeURIComponent(defaultText)}`;
  window.open(url, '_blank');
}

export function WhatsAppButton({ phone, name, message, className = '' }: WhatsAppButtonProps) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        openWhatsApp(phone, name, message);
      }}
      className={`px-2 py-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors shadow-xs ${className}`}
      title={`Send WhatsApp message to ${name}`}
    >
      <MessageSquare className="w-3.5 h-3.5" />
      <span>WA</span>
    </button>
  );
}
