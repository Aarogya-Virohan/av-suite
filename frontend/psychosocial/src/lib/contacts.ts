import type { ReferralContact, ReferralContactInput } from './types';

/** "Dr Kavita Rao, Clinical psychologist" */
export function contactLabel(name: string, role: string | null | undefined): string {
  return role ? `${name}, ${role}` : name;
}

/** "+91 98765 43210 · kavita@example.in", or '' when neither is set. */
export function contactReach(c: Pick<ReferralContact, 'phone' | 'email'>): string {
  return [c.phone, c.email].filter(Boolean).join(' · ');
}

/** Form text to API body: trims, and empty optional fields become null. */
export function toContactInput(form: Record<keyof ReferralContactInput, string>): ReferralContactInput {
  const opt = (v: string) => (v.trim() ? v.trim() : null);
  return {
    name: form.name.trim(),
    role: form.role.trim(),
    phone: opt(form.phone),
    email: opt(form.email),
    note: opt(form.note),
  };
}

/** The same rules the API applies, so the form can say what is missing before saving. */
export function contactProblem(input: ReferralContactInput): string | null {
  if (!input.name) return 'Add a name.';
  if (!input.role) return 'Add a role, for example Clinical psychologist.';
  if (!input.phone && !input.email) return 'Add a phone number or an email address.';
  if (input.phone) {
    const digits = input.phone.replace(/\D/g, '').length;
    if (!/^\+?[0-9 -]+$/.test(input.phone) || digits < 6 || digits > 20) {
      return 'Enter a phone number with 6 to 20 digits.';
    }
  }
  if (input.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.email)) return 'Enter a valid email address.';
  return null;
}
