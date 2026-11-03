import type { InstrumentId, Scale } from './types';

/**
 * Severity is shown with a label, an icon and a filled-segment meter, never
 * by colour alone (SRS 3.6, 4.1.2). Tone only reinforces what the label and
 * the number of filled segments already say.
 */
export type SeverityTone = 'ok' | 'info' | 'warn' | 'danger';

/** Number of bands per scale, from the published instruments. */
export function bandCount(instrumentId: InstrumentId, scaleId: string): number {
  if (instrumentId === 'gad7') return 4;
  if (instrumentId === 'phq9') return 5;
  void scaleId; // every DASS-21 subscale has five bands
  return 5;
}

export function toneFor(level: number, referral: boolean): SeverityTone {
  if (referral || level >= 3) return 'danger';
  if (level === 2) return 'warn';
  if (level === 1) return 'info';
  return 'ok';
}

export function scoreDelta(current: Scale, baseline: Scale | undefined): number | null {
  if (!baseline) return null;
  return current.score - baseline.score;
}

/** Plain words for the change since baseline. Lower scores mean fewer symptoms. */
export function deltaWords(delta: number | null): string {
  if (delta === null) return '';
  if (delta === 0) return 'No change from baseline';
  const points = Math.abs(delta) === 1 ? 'point' : 'points';
  return delta < 0 ? `${Math.abs(delta)} ${points} lower than baseline` : `${delta} ${points} higher than baseline`;
}

export const PATIENT_TITLES: Record<InstrumentId, { title: string; blurb: string; minutes: number }> = {
  phq9: { title: 'How you have been feeling', blurb: 'Mood, energy, sleep and interest in things.', minutes: 2 },
  gad7: { title: 'Worry and nervousness', blurb: 'How often worry or tension has bothered you.', minutes: 2 },
  dass21: { title: 'Stress, worry and mood', blurb: 'A wider look at stress, tension and low mood.', minutes: 5 },
};

export const STAFF_INSTRUMENTS: Record<InstrumentId, { screensFor: string }> = {
  phq9: { screensFor: 'Depression' },
  gad7: { screensFor: 'Anxiety' },
  dass21: { screensFor: 'Depression, anxiety and stress' },
};

export const REFERRAL_LABELS = {
  referred_gp: 'Referred to GP',
  referred_psychologist: 'Referred to psychologist',
  referred_psychiatrist: 'Referred to psychiatrist',
  already_under_care: 'Already under mental health care',
  patient_declined: 'Patient declined referral',
  monitor_and_rescreen: 'Monitor and re-screen',
  other: 'Other',
} as const;
