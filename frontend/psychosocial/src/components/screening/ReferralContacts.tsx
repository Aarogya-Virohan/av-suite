'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { Archive, Loader2, Pencil, Plus, RotateCcw, UserRound } from 'lucide-react';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { contactProblem, contactReach, toContactInput } from '@/lib/contacts';
import type { ReferralContact } from '@/lib/types';
import { Badge, Button, Card, CardHeader, FieldLabel, inputClass } from '@/components/ui/brand';
import { SlideOver } from '@/components/ui/SlideOver';
import { InfoNote } from './indicators';

const URL = '/psychosocial/settings/referral-contacts';
type FormState = { name: string; role: string; phone: string; email: string; note: string };
const EMPTY: FormState = { name: '', role: '', phone: '', email: '', note: '' };

function fromContact(c: ReferralContact): FormState {
  return { name: c.name, role: c.role, phone: c.phone ?? '', email: c.email ?? '', note: c.note ?? '' };
}

/** Clinic referral contact directory on the Settings page (SRS 4.3.1). */
export function ReferralContacts() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<ReferralContact | 'new' | null>(null);
  const contacts = useQuery({ queryKey: ['referral-contacts-admin'], queryFn: () => api.get<ReferralContact[]>(URL) });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['referral-contacts-admin'] });
    qc.invalidateQueries({ queryKey: ['referral-contacts'] });
  };
  const archive = useMutation({
    mutationFn: (c: ReferralContact) => api.post<ReferralContact>(`${URL}/${c.id}/${c.archived ? 'restore' : 'archive'}`),
    onSuccess: (c) => {
      toast.success(c.archived ? `${c.name} archived.` : `${c.name} restored.`);
      refresh();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <Card className="p-5">
      <CardHeader
        title="Referral contacts"
        action={
          <Button variant="secondary" className="h-9" onClick={() => setEditing('new')}>
            <Plus className="h-4 w-4" />
            Add contact
          </Button>
        }
      />
      <p className="text-sm text-muted">
        People and services your physios refer patients to. They pick one when they record a referral. Archived
        contacts drop out of that list, and past referrals keep the name they were saved with.
      </p>

      {contacts.isPending ? (
        <Loader2 className="mt-4 h-5 w-5 animate-spin text-grove" aria-label="Loading" />
      ) : contacts.isError ? (
        <p className="mt-4 text-sm text-danger">{contacts.error.message}</p>
      ) : contacts.data.length === 0 ? (
        <p className="mt-4 text-sm text-muted">No contacts yet.</p>
      ) : (
        <ul className="mt-4 divide-y divide-line">
          {contacts.data.map((c) => (
            <li key={c.id} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
              <div className={cn('min-w-0', c.archived && 'opacity-70')}>
                <p className="flex flex-wrap items-center gap-2 font-semibold text-ink">
                  <UserRound className="h-4 w-4 text-muted" aria-hidden="true" />
                  {c.name}
                  <span className="font-normal text-muted">{c.role}</span>
                  {c.archived ? <Badge tone="neutral">Archived</Badge> : null}
                </p>
                <p className="mt-0.5 break-all text-sm text-ink-2">{contactReach(c)}</p>
                {c.note ? <p className="mt-0.5 text-xs text-muted">{c.note}</p> : null}
              </div>
              <div className="flex gap-1">
                <Button variant="ghost" className="h-9" onClick={() => setEditing(c)} aria-label={`Edit ${c.name}`}>
                  <Pencil className="h-4 w-4" />
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  className="h-9"
                  onClick={() => archive.mutate(c)}
                  disabled={archive.isPending}
                  aria-label={`${c.archived ? 'Restore' : 'Archive'} ${c.name}`}
                >
                  {c.archived ? <RotateCcw className="h-4 w-4" /> : <Archive className="h-4 w-4" />}
                  {c.archived ? 'Restore' : 'Archive'}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <SlideOver
        isOpen={editing !== null}
        onClose={() => setEditing(null)}
        title={editing === 'new' ? 'Add a referral contact' : 'Edit referral contact'}
      >
        {editing !== null ? (
          <ContactForm
            contact={editing === 'new' ? null : editing}
            onSaved={() => {
              refresh();
              setEditing(null);
            }}
          />
        ) : null}
      </SlideOver>
    </Card>
  );
}

function ContactForm({ contact, onSaved }: { contact: ReferralContact | null; onSaved: () => void }) {
  const [form, setForm] = useState<FormState>(contact ? fromContact(contact) : EMPTY);
  const [problem, setProblem] = useState<string | null>(null);
  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((cur) => ({ ...cur, [key]: e.target.value }));
    setProblem(null);
  };

  const save = useMutation({
    mutationFn: () => {
      const body = toContactInput(form);
      return contact ? api.put<ReferralContact>(`${URL}/${contact.id}`, body) : api.post<ReferralContact>(URL, body);
    },
    onSuccess: (c) => {
      toast.success(contact ? `${c.name} updated.` : `${c.name} added.`);
      onSaved();
    },
    onError: (e: Error) => setProblem(e.message),
  });

  const fields: { key: keyof FormState; label: string; type?: string; hint?: string; max: number }[] = [
    { key: 'name', label: 'Name', max: 120 },
    { key: 'role', label: 'Role', hint: 'For example Clinical psychologist, Psychiatrist, GP', max: 80 },
    { key: 'phone', label: 'Phone', type: 'tel', max: 32 },
    { key: 'email', label: 'Email', type: 'email', max: 254 },
  ];

  return (
    <form
      className="space-y-4"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        const issue = contactProblem(toContactInput(form));
        setProblem(issue);
        if (!issue) save.mutate();
      }}
    >
      {problem ? (
        <p role="alert" className="rounded-[10px] bg-danger-wash px-3 py-2 text-sm text-danger">
          {problem}
        </p>
      ) : null}
      {fields.map((f) => (
        <div key={f.key}>
          <FieldLabel htmlFor={`contact-${f.key}`}>{f.label}</FieldLabel>
          <input
            id={`contact-${f.key}`}
            type={f.type ?? 'text'}
            className={inputClass}
            value={form[f.key]}
            maxLength={f.max}
            onChange={set(f.key)}
            autoComplete="off"
          />
          {f.hint ? <p className="mt-1 text-xs text-muted">{f.hint}</p> : null}
        </div>
      ))}
      <InfoNote>A phone number or an email address is needed, or both.</InfoNote>
      <div>
        <FieldLabel htmlFor="contact-note">Note (optional)</FieldLabel>
        <textarea
          id="contact-note"
          rows={3}
          maxLength={500}
          value={form.note}
          onChange={set('note')}
          className={cn(inputClass, 'h-auto py-2')}
          placeholder="For example, days available or how to book"
        />
      </div>
      <Button type="submit" className="w-full" disabled={save.isPending}>
        {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        {contact ? 'Save changes' : 'Add contact'}
      </Button>
    </form>
  );
}
