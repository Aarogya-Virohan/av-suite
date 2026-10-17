'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, X, Users, Calendar, CreditCard } from 'lucide-react';
import { usePatients } from '../../features/patients/api';
import { canAccessModule, hasCapability, type ModuleVisibility, usePermissionSubscription } from '../../config/permissions';
import { Avatar, Badge, type BadgeTone } from '../ui/brand';

const STATUS_TONE: Record<string, BadgeTone> = { active: 'ok', inactive: 'neutral', discharged: 'info' };

const QUICK_ACTIONS: { label: string; href: string; module: keyof ModuleVisibility; icon: React.ElementType; tone: string }[] = [
  { label: 'Go to Patient Directory', href: '/patients', module: 'patients', icon: Users, tone: 'bg-logo-teal-wash text-logo-teal-ink' },
  { label: 'Go to Appointments Calendar', href: '/appointments', module: 'appointments', icon: Calendar, tone: 'bg-info-wash text-info' },
  { label: 'Go to Billing & Invoices', href: '/billing', module: 'billing', icon: CreditCard, tone: 'bg-grove-wash text-grove' },
];

/*
 * Restyled to the AV Suite theme. Quick actions now follow the same module
 * permissions as the sidebar (they used to offer Billing to every role), and
 * patient search only runs for roles with patients.view (L-29).
 */
export function CommandBar() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const router = useRouter();
  usePermissionSubscription(); // Decisions.md D-013
  const canSearchPatients = hasCapability('patients.view');
  // Only search while the palette is open, and only for roles that can view
  // patients. It used to call /patients on every page load (403 for staff
  // without patients.view, L-29).
  const { data: response, isFetching } = usePatients(search, 1, 5, isOpen && canSearchPatients);
  const filteredPatients = response?.data || [];
  const actions = QUICK_ACTIONS.filter((a) => canAccessModule(a.module));

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!isOpen) return null;

  const navigate = (path: string) => {
    router.push(path);
    setIsOpen(false);
    setSearch('');
  };

  const rowClass =
    'flex w-full cursor-pointer items-center gap-3 rounded-[9px] px-3 py-2 text-left text-sm text-ink-2 transition-colors hover:bg-canvas';

  return (
    <div className="modal-backdrop z-50" onClick={() => setIsOpen(false)}>
      <div
        className="modal-card w-full max-w-xl p-4"
        role="dialog"
        aria-modal="true"
        aria-label="Search and commands"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div className="flex items-center gap-3 border-b border-line pb-3">
          <Search className="h-5 w-5 text-slate-400" />
          <input
            type="text"
            placeholder={canSearchPatients ? 'Search patients by name or phone...' : 'Jump to a page...'}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent text-sm text-ink placeholder:text-slate-400 focus:outline-none"
            autoFocus
          />
          <button
            onClick={() => setIsOpen(false)}
            aria-label="Close"
            className="cursor-pointer rounded-md p-1 text-slate-400 transition-colors hover:bg-canvas hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-80 space-y-4 overflow-y-auto py-3">
          {actions.length > 0 && (
            <div>
              <p className="mb-1 px-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted">Quick actions</p>
              <div className="space-y-0.5">
                {actions.map((a) => {
                  const Icon = a.icon;
                  return (
                    <button key={a.href} onClick={() => navigate(a.href)} className={rowClass}>
                      <span className={`grid h-7 w-7 place-items-center rounded-lg ${a.tone}`}>
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="font-medium">{a.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {canSearchPatients && (
            <div>
              <p className="mb-1 px-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-muted">
                Patients ({filteredPatients.length})
              </p>
              {filteredPatients.length === 0 ? (
                <p className="px-3 py-2 text-xs text-muted">
                  {isFetching ? 'Searching...' : search ? 'No patients match this search.' : 'Start typing to search patients.'}
                </p>
              ) : (
                <div className="space-y-0.5">
                  {filteredPatients.map((patient) => (
                    <button
                      key={patient.id}
                      onClick={() => navigate(`/patients/${patient.id}`)}
                      className={`${rowClass} justify-between`}
                    >
                      <span className="flex min-w-0 items-center gap-2.5">
                        <Avatar name={`${patient.first_name} ${patient.last_name}`} size={28} />
                        <span className="truncate font-semibold text-ink">
                          {patient.first_name} {patient.last_name}
                        </span>
                        <span className="text-xs text-muted tabular-nums">{patient.phone}</span>
                      </span>
                      <Badge tone={STATUS_TONE[patient.status] ?? 'neutral'} className="capitalize">
                        {patient.status}
                      </Badge>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Hint */}
        <div className="flex items-center justify-between border-t border-line pt-2 text-[11px] text-muted">
          <span>
            Press <kbd className="rounded border border-line bg-canvas px-1.5 py-0.5 font-sans">⌘K</kbd> anywhere to open
          </span>
          <span>
            <kbd className="rounded border border-line bg-canvas px-1.5 py-0.5 font-sans">Esc</kbd> to close
          </span>
        </div>
      </div>
    </div>
  );
}
