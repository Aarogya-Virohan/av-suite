'use client';

/*
 * Clinic logo for the reports (Round 4, BR-b + BR-g, 26 Nov 2026).
 *
 * The picked file is checked on the server (POST /settings/clinic/logo-preview)
 * against the upload rules, resized, and shown on a live copy of the clinical
 * report band in the chosen background mode. Nothing is saved until the
 * Settings form is saved; then the resized copy is sent.
 */

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import {
  LOGO_BG_OPTIONS,
  LOGO_HELPER_TEXT,
  LOGO_TYPES,
  LOGO_UPLOAD_MAX_BYTES,
  previewLogo,
  type LogoBgMode,
} from '../api';
import { asset } from '../../../lib/hub';

// Same colours as the PDF band (backend app/services/brand.py).
const BAND = 'linear-gradient(90deg, #0b1238 0%, #1b4a54 100%)';

export interface LogoLetterheadFieldProps {
  /** The logo to save: null = no logo. A data URI or an older https link. */
  logo: string | null;
  mode: LogoBgMode;
  canEdit: boolean;
  /** Warning for the saved logo + mode, from GET /settings/clinic. */
  savedLowContrast: boolean;
  /** True while the logo and mode are the saved ones. */
  isSaved: boolean;
  doctorName: string;
  phone: string;
  email: string;
  onLogoChange: (logo: string | null) => void;
  onModeChange: (mode: LogoBgMode) => void;
}

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function LogoLetterheadField({
  logo,
  mode,
  canEdit,
  savedLowContrast,
  isSaved,
  doctorName,
  phone,
  email,
  onLogoChange,
  onModeChange,
}: LogoLetterheadFieldProps) {
  // The file as picked, kept so a mode change is judged on the original.
  const [source, setSource] = React.useState<string | null>(null);
  const [bandLogo, setBandLogo] = React.useState<string | null>(null);
  const [lowContrast, setLowContrast] = React.useState<boolean | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const request = React.useRef(0);

  const refresh = React.useCallback(async (value: string, nextMode: LogoBgMode) => {
    const id = ++request.current;
    setBusy(true);
    try {
      const out = await previewLogo(value, nextMode);
      if (id !== request.current) return null;
      setBandLogo(out.letterhead_logo);
      setLowContrast(out.low_contrast);
      setError(null);
      return out;
    } catch (err: any) {
      if (id === request.current) setError(err?.message || 'This image could not be checked.');
      return null;
    } finally {
      if (id === request.current) setBusy(false);
    }
  }, []);

  // A saved data-URI logo: show it on the band in the saved mode.
  React.useEffect(() => {
    if (!logo || source) return;
    if (logo.startsWith('data:')) void refresh(logo, mode);
    else setBandLogo(logo);
    // Only when the saved logo changes; mode changes go through changeMode.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logo]);

  const pick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (!LOGO_TYPES.includes(file.type)) {
      setError('Please upload the logo as a PNG, JPG or WebP image.');
      return;
    }
    if (file.size > LOGO_UPLOAD_MAX_BYTES) {
      setError('The logo file is larger than 2 MB. Please choose a smaller file.');
      return;
    }
    const raw = await readAsDataUrl(file);
    const out = await refresh(raw, mode);
    if (out) {
      setSource(raw);
      onLogoChange(out.logo);
      toast.success('Logo ready. Save to apply it.');
    }
  };

  const changeMode = (next: LogoBgMode) => {
    onModeChange(next);
    const value = source || (logo && logo.startsWith('data:') ? logo : null);
    if (value) void refresh(value, next);
  };

  const remove = () => {
    request.current += 1;
    setSource(null);
    setBandLogo(null);
    setLowContrast(null);
    setError(null);
    onLogoChange(null);
  };

  const warn = lowContrast ?? (isSaved ? savedLowContrast : false);
  const contacts = [phone.trim(), email.trim()].filter(Boolean).join('  ·  ');

  return (
    <div className="space-y-3">
      <div>
        <label htmlFor="clinic-logo" className="mb-1.5 block text-xs font-semibold text-ink">
          Clinic logo
        </label>
        <p className="mb-2 text-xs text-muted">{LOGO_HELPER_TEXT}</p>
        {canEdit && (
          <input
            id="clinic-logo"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={pick}
            className="w-full cursor-pointer text-xs text-muted file:mr-4 file:cursor-pointer file:rounded-lg file:border-0 file:bg-grove-wash file:px-4 file:py-2 file:text-xs file:font-semibold file:text-grove hover:file:bg-[#d3eedc]"
          />
        )}
        {error && (
          <p role="alert" className="mt-2 text-xs font-semibold text-danger">
            {error}
          </p>
        )}
      </div>

      {logo && (
        <fieldset disabled={!canEdit || busy} className="min-w-0">
          <legend className="mb-1.5 block text-xs font-semibold text-ink">Logo background on reports</legend>
          <div role="radiogroup" className="grid gap-2 sm:grid-cols-3">
            {LOGO_BG_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`flex cursor-pointer items-start gap-2 rounded-xl border px-3 py-2.5 text-xs ${
                  mode === opt.value ? 'border-grove bg-grove-wash' : 'border-line bg-canvas'
                }`}
              >
                <input
                  type="radio"
                  name="logo-bg-mode"
                  value={opt.value}
                  checked={mode === opt.value}
                  onChange={() => changeMode(opt.value)}
                  className="mt-0.5"
                />
                <span>
                  <span className="block font-semibold text-ink">{opt.label}</span>
                  <span className="text-muted">{opt.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <div>
        <p className="mb-1.5 text-xs font-semibold text-ink">Report letterhead preview</p>
        <div
          data-testid="letterhead-preview"
          className="flex h-16 items-center gap-3 overflow-hidden rounded-lg px-3"
          style={{ background: BAND }}
        >
          {bandLogo && (
            <div className="flex h-11 w-28 shrink-0 items-center">
              <span className={mode === 'white' ? 'inline-flex rounded bg-white p-1' : 'inline-flex'}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={bandLogo} alt="Clinic logo on the report band" className="max-h-9 max-w-[104px] object-contain" />
              </span>
            </div>
          )}
          <div className="w-0 min-w-0 flex-1 leading-tight">
            <p className="truncate text-sm font-bold text-white">{doctorName.trim() || 'Clinic owner admin'}</p>
            {contacts && <p className="truncate text-[11px] text-[#c9d0ea]">{contacts}</p>}
          </div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={asset('/brand/av-logo-mark.png')} alt="" className="h-8 w-8 shrink-0 object-contain opacity-90" />
        </div>
        {busy && <p className="mt-1.5 text-xs text-muted">Checking the logo…</p>}
        {logo && warn && !busy && (
          <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-2 text-xs text-amber-900">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            This logo is hard to see on the dark report band. Try &quot;White background&quot;, or upload a version
            with light colours or a transparent background.
          </p>
        )}
      </div>

      {logo && canEdit && (
        <button type="button" onClick={remove} className="cursor-pointer text-xs font-semibold text-danger hover:underline">
          Remove logo
        </button>
      )}
    </div>
  );
}
