"use client";

import React, { useState } from "react";
import { Loader2 } from "lucide-react";
import { Patient } from "@/types/exercise";
import { createPatient } from "@/lib/api";

// Same rules as before the redesign.
const NAME_PATTERN = /^[A-Za-z][A-Za-z .'-]{0,99}$/;
const PHONE_PATTERN = /^[0-9]{10}$/;

const input =
  "h-10 w-full rounded-[10px] border border-line bg-card px-3 text-sm text-ink placeholder:text-[#8a8fa6] transition-colors focus:border-grove focus:outline-none focus:ring-2 focus:ring-grove/15";
const label = "mb-1 block text-[11px] font-bold uppercase tracking-wide text-muted-foreground";

interface AddPatientFormProps {
  onCancel: () => void;
  onCreated: (patient: Patient) => void;
}

export function AddPatientForm({ onCancel, onCreated }: AddPatientFormProps) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const first = firstName.trim();
    const last = lastName.trim();
    if (!first || !last) return setError("First and last name are required.");
    if (!NAME_PATTERN.test(first) || !NAME_PATTERN.test(last)) {
      return setError("Names may only contain letters, spaces, hyphens, apostrophes and periods.");
    }
    if (phone && !PHONE_PATTERN.test(phone)) return setError("Phone number must be exactly 10 digits.");
    setError(null);
    setSaving(true);
    try {
      const created = await createPatient({
        first_name: first,
        last_name: last,
        phone: phone || undefined,
        date_of_birth: dateOfBirth || undefined,
      });
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add the patient.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-3 rounded-xl border border-line bg-card p-3.5">
      <p className="text-sm font-semibold text-ink">New patient</p>
      <div className="grid grid-cols-2 gap-2">
        <label className="block">
          <span className={label}>First name</span>
          <input
            className={input}
            autoFocus
            autoComplete="off"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value.replace(/[^A-Za-z .'-]/g, ""))}
          />
        </label>
        <label className="block">
          <span className={label}>Last name</span>
          <input
            className={input}
            autoComplete="off"
            value={lastName}
            onChange={(e) => setLastName(e.target.value.replace(/[^A-Za-z .'-]/g, ""))}
          />
        </label>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="block">
          <span className={label}>Phone (optional)</span>
          <input
            className={input}
            type="tel"
            inputMode="numeric"
            maxLength={10}
            placeholder="10 digits"
            value={phone}
            onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 10))}
          />
        </label>
        <label className="block">
          <span className={label}>Date of birth (optional)</span>
          <input
            className={input}
            type="date"
            max={new Date().toISOString().slice(0, 10)}
            value={dateOfBirth}
            onChange={(e) => setDateOfBirth(e.target.value)}
          />
        </label>
      </div>
      {error && (
        <p role="alert" className="text-xs font-medium text-danger">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="h-9 cursor-pointer rounded-lg border border-line px-3 text-sm font-semibold text-ink-2 hover:bg-muted"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="flex h-9 cursor-pointer items-center gap-1.5 rounded-lg bg-grove px-3.5 text-sm font-semibold text-white shadow-primary hover:bg-grove-hover disabled:opacity-60"
        >
          {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          Add patient
        </button>
      </div>
    </form>
  );
}
