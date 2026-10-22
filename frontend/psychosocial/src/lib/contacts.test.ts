import { describe, expect, it } from 'vitest';
import { contactLabel, contactProblem, contactReach, toContactInput } from './contacts';

const form = { name: ' Dr Kavita Rao ', role: 'Clinical psychologist', phone: '+91 98765 43210', email: ' ', note: '' };

describe('referral contacts', () => {
  it('labels and reach lines', () => {
    expect(contactLabel('Dr Kavita Rao', 'Clinical psychologist')).toBe('Dr Kavita Rao, Clinical psychologist');
    expect(contactLabel('Dr Kavita Rao', null)).toBe('Dr Kavita Rao');
    expect(contactReach({ phone: '+91 98765 43210', email: 'k@x.in' })).toBe('+91 98765 43210 · k@x.in');
    expect(contactReach({ phone: null, email: 'k@x.in' })).toBe('k@x.in');
  });

  it('turns form text into the API body', () => {
    expect(toContactInput(form)).toEqual({
      name: 'Dr Kavita Rao',
      role: 'Clinical psychologist',
      phone: '+91 98765 43210',
      email: null,
      note: null,
    });
  });

  it('checks what the API checks', () => {
    const ok = toContactInput(form);
    expect(contactProblem(ok)).toBeNull();
    expect(contactProblem({ ...ok, name: '' })).toBe('Add a name.');
    expect(contactProblem({ ...ok, phone: null, email: null })).toBe('Add a phone number or an email address.');
    expect(contactProblem({ ...ok, phone: '12345' })).toBe('Enter a phone number with 6 to 20 digits.');
    expect(contactProblem({ ...ok, phone: '98+7654321' })).toBe('Enter a phone number with 6 to 20 digits.');
    expect(contactProblem({ ...ok, phone: null, email: 'nope' })).toBe('Enter a valid email address.');
    expect(contactProblem({ ...ok, phone: null, email: 'help@clinic.in' })).toBeNull();
  });
});
