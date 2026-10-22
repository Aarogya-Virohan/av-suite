import { describe, expect, it } from 'vitest';
import { bandCount, deltaWords, toneFor } from './severity';
import { whatsappLink } from './whatsapp';

describe('severity presentation', () => {
  it('uses the published band counts', () => {
    expect(bandCount('phq9', 'total')).toBe(5);
    expect(bandCount('gad7', 'total')).toBe(4);
    expect(bandCount('dass21', 'stress')).toBe(5);
  });

  it('marks referral-level results as danger whatever the band', () => {
    expect(toneFor(2, true)).toBe('danger');
    expect(toneFor(0, false)).toBe('ok');
    expect(toneFor(1, false)).toBe('info');
    expect(toneFor(2, false)).toBe('warn');
    expect(toneFor(4, false)).toBe('danger');
  });

  it('describes the change from baseline in words', () => {
    expect(deltaWords(null)).toBe('');
    expect(deltaWords(0)).toBe('No change from baseline');
    expect(deltaWords(-1)).toBe('1 point lower than baseline');
    expect(deltaWords(5)).toBe('5 points higher than baseline');
  });
});

describe('whatsapp link', () => {
  it('normalises Indian numbers', () => {
    expect(whatsappLink('98765 43210', 'hi')).toBe('https://wa.me/919876543210?text=hi');
    expect(whatsappLink('+91 98765-43210', 'hi')).toBe('https://wa.me/919876543210?text=hi');
    expect(whatsappLink('12345', 'hi')).toBeNull();
    expect(whatsappLink(null, 'hi')).toBeNull();
  });
});
