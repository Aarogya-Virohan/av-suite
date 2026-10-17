'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { Calendar, CheckCircle2, Loader2, ShieldAlert, Stethoscope } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '../../../../lib/api-client';
import { Button, FieldLabel, inputClass } from '../../../../components/ui/brand';
import { cn } from '../../../../lib/cn';

interface ClinicBranding {
  clinic_id: string;
  name: string;
  logo_url: string | null;
  brand_color: string | null;
}

const SERVICES = ['Physiotherapy Consultation', 'Spine & Back Rehab', 'Sports Injury Rehab', 'Post-Operative Therapy'];
const SLOTS = ['09:00 AM', '10:00 AM', '11:30 AM', '02:00 PM', '04:00 PM', '06:00 PM'];

/** Today in the visitor's own time zone (toISOString() is UTC and gave yesterday before 5:30 am IST). */
function localToday(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const prettyDate = (value: string) => {
  const [y, m, d] = value.split('-').map(Number);
  const date = new Date(y, (m || 1) - 1, d || 1);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }).format(date);
};

export default function PublicBookingPage() {
  const params = useParams();
  const clinicSlug = (params?.clinicSlug as string) || '';

  // The clinic is verified with the server before the form is shown, and its
  // real name comes from the server. Previously the name was built from the URL
  // text, so a patient could not see which clinic would receive their details.
  const [clinic, setClinic] = useState<ClinicBranding | null>(null);
  const [clinicState, setClinicState] = useState<'loading' | 'ready' | 'not_found' | 'error'>('loading');

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [service, setService] = useState(SERVICES[0]);
  const [preferredDate, setPreferredDate] = useState('');
  const [preferredSlot, setPreferredSlot] = useState('10:00 AM');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('male');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const turnstileSiteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;
  const [minDate, setMinDate] = useState('');

  // Dates are set after mount so server and client markup match.
  React.useEffect(() => {
    const today = localToday();
    setMinDate(today);
    setPreferredDate((prev) => prev || today);
  }, []);

  React.useEffect(() => {
    if (!clinicSlug) {
      setClinicState('not_found');
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await apiClient.get(`/booking/branding/${encodeURIComponent(clinicSlug)}`);
        const data = (res.data?.data ?? res.data) as ClinicBranding | undefined;
        if (cancelled) return;
        if (data?.clinic_id) {
          setClinic(data);
          setClinicState('ready');
        } else {
          setClinicState('not_found');
        }
      } catch (err: any) {
        if (!cancelled) setClinicState(err?.response?.status === 404 ? 'not_found' : 'error');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [clinicSlug]);

  React.useEffect(() => {
    if (!turnstileSiteKey || typeof window === 'undefined') return;

    if (!document.getElementById('cf-turnstile-script')) {
      const script = document.createElement('script');
      script.id = 'cf-turnstile-script';
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }

    const interval = setInterval(() => {
      if ((window as any).turnstile) {
        clearInterval(interval);
        const container = document.getElementById('turnstile-container');
        if (container && !container.hasChildNodes()) {
          (window as any).turnstile.render('#turnstile-container', {
            sitekey: turnstileSiteKey,
            callback: (token: string) => {
              setTurnstileToken(token);
            },
          });
        }
      }
    }, 100);

    return () => clearInterval(interval);
  }, [turnstileSiteKey, step]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting || !clinic) return;

    if (turnstileSiteKey && !turnstileToken) {
      toast.error('Please complete the security check');
      return;
    }

    if (!name || !phone || !chiefComplaint) {
      toast.error('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    try {
      // Submit to the exact clinic verified on load and shown to the patient.
      await apiClient.post(`/booking/request?clinic_id=${clinic.clinic_id}`, {
        name: name,
        phone: phone,
        age: age ? parseInt(age) : null,
        gender: gender,
        chief_complaint: chiefComplaint,
        preferred_date: preferredDate,
        preferred_slot: preferredSlot,
        notes: `Service Requested: ${service}`,
        turnstile_token: turnstileToken || undefined,
      });

      setIsSuccess(true);
      toast.success('Appointment request submitted!');
    } catch (err) {
      console.error(err);
      toast.error('Failed to submit appointment request');
      setIsSubmitting(false);
    }
  };

  const headerColor = clinic?.brand_color || '#0b1238';

  const shell = (children: React.ReactNode) => (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-4 md:p-8">
      <div className="w-full max-w-lg overflow-hidden rounded-2xl border border-line bg-card shadow-hero">{children}</div>
    </div>
  );

  if (clinicState === 'loading') {
    return shell(
      <div className="flex items-center justify-center gap-2 p-12 text-sm text-muted">
        <Loader2 className="h-5 w-5 animate-spin text-grove" /> Loading booking page...
      </div>,
    );
  }

  if (clinicState !== 'ready' || !clinic) {
    return shell(
      <div className="space-y-3 p-8 text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-danger-wash text-danger">
          <ShieldAlert className="h-7 w-7" />
        </div>
        <h1 className="font-display text-xl font-bold text-ink">
          {clinicState === 'not_found' ? 'Booking page not found' : 'Booking page unavailable'}
        </h1>
        <p className="text-sm text-muted">
          {clinicState === 'not_found'
            ? 'This booking link is not valid. Please check the link with your clinic.'
            : 'We could not load this booking page. Please try again in a moment.'}
        </p>
      </div>,
    );
  }

  const header = (
    <div className="flex items-center gap-3 px-6 py-5 text-white md:px-8" style={{ background: headerColor }}>
      <span className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl bg-white p-1">
        {clinic.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={clinic.logo_url} alt="" className="h-full w-full object-contain" />
        ) : (
          <Stethoscope className="h-5 w-5 text-grove" />
        )}
      </span>
      <div className="min-w-0">
        <h1 className="truncate font-display text-lg font-bold">{clinic.name}</h1>
        <p className="text-xs text-white/75">Request an appointment online</p>
      </div>
    </div>
  );

  if (isSuccess) {
    return shell(
      <>
        {header}
        <div className="space-y-4 p-8 text-center">
          <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-ok-wash text-ok">
            <CheckCircle2 className="h-9 w-9" />
          </div>
          <h2 className="font-display text-2xl font-bold text-ink">Booking Requested!</h2>
          <p className="text-sm leading-relaxed text-muted">
            Thank you, <strong className="text-ink">{name}</strong>. The team at{' '}
            <span className="font-semibold text-grove">{clinic.name}</span> will contact you at{' '}
            <strong className="text-ink">{phone}</strong> to confirm your slot for {prettyDate(preferredDate)} at{' '}
            {preferredSlot}.
          </p>
        </div>
      </>,
    );
  }

  const steps = ['Service', 'Time', 'Details'];

  return shell(
    <>
      {header}
      <div className="space-y-6 p-6 md:p-8">
        <ol className="flex items-center gap-2" aria-label="Booking steps">
          {steps.map((label, i) => {
            const n = (i + 1) as 1 | 2 | 3;
            const done = step > n;
            const active = step === n;
            return (
              <li key={label} className="flex flex-1 items-center gap-2">
                <span
                  className={cn(
                    'grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-bold',
                    done ? 'bg-grove text-white' : active ? 'bg-grove-wash text-grove ring-2 ring-grove' : 'bg-slate-100 text-slate-400',
                  )}
                >
                  {n}
                </span>
                <span className={cn('text-xs font-semibold', active || done ? 'text-ink' : 'text-slate-400')}>{label}</span>
                {i < steps.length - 1 && <span className="h-px flex-1 bg-line" aria-hidden="true" />}
              </li>
            );
          })}
        </ol>

        <form onSubmit={handleSubmit} className="space-y-5">
          {step === 1 && (
            <div className="space-y-2.5">
              <FieldLabel>Select Service</FieldLabel>
              {SERVICES.map((s) => (
                <button
                  type="button"
                  key={s}
                  onClick={() => {
                    setService(s);
                    setStep(2);
                  }}
                  className={cn(
                    'flex w-full cursor-pointer items-center justify-between rounded-xl border p-3.5 text-left text-sm font-semibold transition-colors',
                    service === s ? 'border-grove bg-grove-wash text-grove' : 'border-line text-ink-2 hover:bg-canvas',
                  )}
                >
                  <span>{s}</span>
                  <Calendar className="h-4 w-4" />
                </button>
              ))}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <FieldLabel htmlFor="pref-date">Preferred Date</FieldLabel>
                <input
                  id="pref-date"
                  type="date"
                  value={preferredDate}
                  min={minDate || undefined}
                  onChange={(e) => setPreferredDate(e.target.value)}
                  className={inputClass}
                />
              </div>

              <div>
                <FieldLabel>Preferred Time Slot</FieldLabel>
                <div className="grid grid-cols-3 gap-2">
                  {SLOTS.map((slot) => (
                    <button
                      type="button"
                      key={slot}
                      onClick={() => setPreferredSlot(slot)}
                      aria-pressed={preferredSlot === slot}
                      className={cn(
                        'cursor-pointer rounded-lg border p-2 text-xs font-bold transition-colors',
                        preferredSlot === slot ? 'border-grove bg-grove text-white' : 'border-line text-ink-2 hover:bg-canvas',
                      )}
                    >
                      {slot}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <Button type="button" variant="ghost" onClick={() => setStep(1)}>
                  Back
                </Button>
                <Button type="button" onClick={() => setStep(3)} disabled={!preferredDate}>
                  Next: Enter Details
                </Button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div>
                <FieldLabel htmlFor="bk-name">Your Full Name *</FieldLabel>
                <input
                  id="bk-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Ramesh Shah"
                  className={inputClass}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <FieldLabel htmlFor="bk-phone">Phone Number *</FieldLabel>
                  <input
                    id="bk-phone"
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="10-digit mobile"
                    className={inputClass}
                  />
                </div>
                <div>
                  <FieldLabel htmlFor="bk-age">Age</FieldLabel>
                  <input
                    id="bk-age"
                    type="number"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    placeholder="e.g. 35"
                    className={inputClass}
                  />
                </div>
              </div>

              <div>
                <FieldLabel htmlFor="bk-gender">Gender</FieldLabel>
                <select id="bk-gender" value={gender} onChange={(e) => setGender(e.target.value)} className={inputClass}>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <FieldLabel htmlFor="bk-complaint">Chief Complaint *</FieldLabel>
                <textarea
                  id="bk-complaint"
                  rows={3}
                  value={chiefComplaint}
                  onChange={(e) => setChiefComplaint(e.target.value)}
                  placeholder="Describe your pain or reason for visit..."
                  className={cn(inputClass, 'h-auto py-2')}
                />
              </div>

              {turnstileSiteKey && <div id="turnstile-container" className="my-3 flex min-h-[65px] justify-center" />}

              <div className="flex items-center justify-between border-t border-line pt-4">
                <Button type="button" variant="ghost" onClick={() => setStep(2)}>
                  Back
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  <span>Submit Appointment Request</span>
                </Button>
              </div>
            </div>
          )}
        </form>
      </div>
    </>,
  );
}
